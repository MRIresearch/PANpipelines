function csvout = enable_aslmetrics(sessions_file,BIDS,panout,project,basil_pipe,basil_csf,csvout)

T = readtable(sessions_file,"FileType","text",'Delimiter', '\t');
num_sessions=height(T);

aslmetrics=struct();

for x = 1:num_sessions
    subject_id=string(T.bids_participant_id(x));
    session_id=string(T.bids_session_id(x));
    site=string(T.shared_projects(x));
    aslfile=glob(sprintf("%s/%s/%s/perf/*asl.nii.gz",BIDS,subject_id,session_id));
    basilasl=glob(sprintf("%s/%s/%s/%s/%s/%s_wf/basil_node/basiloutput/fsl*/asldata_orig.nii.gz",panout,basil_pipe,project,subject_id,session_id,basil_pipe));
    calibfile=glob(sprintf("%s/%s/%s/perf/*m0scan.nii.gz",BIDS,subject_id,session_id));
    basilmask=glob(sprintf("%s/%s/%s/%s/%s/%s_wf/basil_node/basiloutput/fsl*/mask_dil.nii.gz",panout,basil_pipe,project,subject_id,session_id,basil_pipe));
    basilcalib=glob(sprintf("%s/%s/%s/%s/%s/%s_wf/basil_node/basiloutput/fsl*/calib_orig.nii.gz",panout,basil_pipe,project,subject_id,session_id,basil_pipe));
    gmmask_file=glob(sprintf("%s/%s/%s/%s/%s/%s_wf/basil_node/basiloutput/fsl*/pvgm_inasl.nii.gz",panout,basil_pipe,project,subject_id,session_id,basil_pipe));
    wmmask_file=glob(sprintf("%s/%s/%s/%s/%s/%s_wf/basil_node/basiloutput/fsl*/pvwm_inasl.nii.gz",panout,basil_pipe,project,subject_id,session_id,basil_pipe));
    csfmask_file=glob(sprintf("%s/%s/%s/%s/%s/%s_wf/basil_node/basiloutput/calib/refmask.nii.gz",panout,basil_csf,project,subject_id,session_id,basil_csf));
   
    sitehr='UA';
    acq='pasl_prod';
    if site == "002_HML"
        sitehr = 'UM';
    elseif site == "003_HML"
        sitehr = 'EU';
    elseif site == "004_HML"
        sitehr = 'JH';
        acq="pcasl";
    end

    if isfile(aslfile)
       asldata = niftiread(aslfile);
       aslsize = size(asldata);
       aslt=aslsize(4);
    else
       asldata = NaN(128,128,32,20);
       aslsize = [128,128,32]; 
       aslt=20;
    end

   if isfile(calibfile)
       calibdata = niftiread(calibfile);
       calibsize = size(calibdata);
       if length(calibsize) > 3
          calibt=calibsize(4);
       else
          calibt=1;
       end
   elseif isfile(aslfile)
       calibdata = asldata(:,:,:,1);
       asldata = asldata(:,:,:,2:21);
       aslsize = [128,128,32,20]; 
       calibsize = [128,128,32,1]; 
       acq="pasl_plusM0";
       calibt=1;
   else
       calibdata = NaN(128,128,32);
       calibsize = [128,128,32]; 
       calibt=1;
   end

    aslmetrics(x).subject_id=subject_id;
    aslmetrics(x).session_id=session_id;
    aslmetrics(x).site = site;
    aslmetrics(x).sitehr = sitehr;

    aslmetrics(x).acq = acq;
    aslmetrics(x).aslsize = aslsize;
    aslmetrics(x).asldata = asldata;
    aslmetrics(x).aslt = aslt;
    aslmetrics(x).calibsize = calibsize;
    aslmetrics(x).calibdata = calibdata;
    aslmetrics(x).calibt = calibt;

    % whole image metrics
    ctrldata=double(asldata(:,:,:,1:2:20));
    labeldata=double(asldata(:,:,:,2:2:20));
    diffdata = double(ctrldata - labeldata);
    calibdata = double(calibdata);

    mean_ctrl = validmean(ctrldata(:));
    mean_label = validmean(labeldata(:));
    mean_diff = validmean(diffdata(:));


    if ~isfile(basilmask)
        fprintf("file missing. skipping %s\n",subject_id);
        continue
    end

    negmask = diffdata < 0;
    diffdata_negsup = diffdata;
    diffdata_negsup(negmask) = nan;
    mean_diff_negsup = validmean(diffdata_negsup(:));
    negdata_flat = diffdata(negmask);

    neg_voxels_num = length(negdata_flat)/size(diffdata(:),1);
    neg_voxels_mean = validmean(negdata_flat)/validmean(abs(diffdata));
    neg_voxels_median = validmedian(negdata_flat)/validmean(abs(diffdata));
    neg_voxels_peak = min(negdata_flat)/validmean(abs(diffdata));

    perf = diffdata ./ ctrldata;
    mean_perf = validmean(perf);
    median_perf = validmedian(perf);
    perf_negsup = diffdata_negsup ./ ctrldata;
    mean_perf_negsup = validmean(perf_negsup);
    median_perf_negsup = validmedian(perf_negsup);
    
    % brain mask metrics
    brainii = niftiread(basilmask);
    brainmask = brainii > 0.5;
    aslmetrics(x).brainmask = brainmask;

    sizectrl = size(ctrldata);
    dimt = sizectrl(4);
    brainmask_d = repmat(brainmask,[1,1,1,dimt]);
   
    ctrldata_brain = ctrldata;
    ctrldata_brain(~brainmask_d) = nan;
    labeldata_brain = labeldata;
    labeldata_brain(~brainmask_d) = nan;
    diffdata_brain = diffdata;
    diffdata_brain(~brainmask_d) = nan;
    diffdata_bg = diffdata;
    diffdata_bg(brainmask_d) = nan;

    mean_ctrl_brain = validmean(ctrldata_brain(:));
    mean_label_brain = validmean(labeldata_brain(:));
    mean_diff_brain = validmean(diffdata_brain(:));

    negmask_brain = diffdata_brain < 0;
    diffdata_brain_negsup = diffdata_brain;
    diffdata_brain_negsup(negmask_brain) = nan;
    mean_diff_brain_negsup = validmean(diffdata_brain_negsup(:));
    negdata_brain_flat = diffdata_brain(negmask_brain);

    neg_voxels_brain_num = length(negdata_brain_flat )/size(diffdata_brain(:),1);
    neg_voxels_brain_mean = validmean(negdata_brain_flat )/validmean(abs(diffdata_brain));
    neg_voxels_brain_median = validmedian(negdata_brain_flat)/validmean(abs(diffdata_brain));
    neg_voxels_brain_peak = min(negdata_brain_flat)/validmean(abs(diffdata_brain));

    perf_brain = diffdata_brain ./ ctrldata_brain;
    mean_perf_brain = validmean(perf_brain);
    median_perf_brain = validmedian(perf_brain);
    perf_brain_negsup = diffdata_brain_negsup ./ ctrldata_brain;
    mean_perf_brain_negsup = validmean(perf_brain_negsup);
    median_perf_brain_negsup = validmedian(perf_brain_negsup);

    % gm mask metrics
    gmbrainii = niftiread(gmmask_file);
    gmbrainmask = gmbrainii > 0.5;
    aslmetrics(x).gmbrainmask = gmbrainmask;
    gmbrainmask_d = repmat(gmbrainmask,[1,1,1,dimt]);

    ctrldata_brain_gm = ctrldata;
    ctrldata_brain_gm(~gmbrainmask_d) = nan;
    labeldata_brain_gm = labeldata;
    labeldata_brain_gm(~gmbrainmask_d) = nan;
    diffdata_brain_gm = diffdata;
    diffdata_brain_gm(~gmbrainmask_d) = nan;

    mean_ctrl_brain_gm = validmean(ctrldata_brain_gm(:));
    mean_label_brain_gm = validmean(labeldata_brain_gm(:));
    mean_diff_brain_gm = validmean(diffdata_brain_gm(:));
    mean_diff_brain_gm_t = validmean(diffdata_brain_gm(:),1);

    negmask_brain_gm = diffdata_brain_gm < 0;
    diffdata_brain_gm_negsup = diffdata_brain_gm;
    diffdata_brain_gm_negsup(negmask_brain_gm) = nan;
    mean_diff_brain_gm_negsup = validmean(diffdata_brain_gm_negsup(:));

    perf_brain_gm = diffdata_brain_gm ./ ctrldata_brain_gm;
    mean_perf_brain_gm = validmean(perf_brain_gm);
    perf_brain_gm_negsup = diffdata_brain_gm_negsup ./ ctrldata_brain_gm;
    mean_perf_brain_gm_negsup = validmean(perf_brain_gm_negsup);

    bg_variance = validvariance(diffdata_bg);
    bg_std = sqrt(bg_variance);
    bg_std_t = sqrt(validvariance(diffdata_bg,1));
    snr_brain_gm = mean_diff_brain_gm/bg_std;
    snr_brain_gm_t = mean_diff_brain_gm_t ./ bg_std_t; 
    tsnr_brain_gm = mean(snr_brain_gm_t);
    
    
    % wm mask metrics
    wmbrainii = niftiread(wmmask_file);
    wmbrainmask = wmbrainii > 0.5;
    aslmetrics(x).wmbrainmask = wmbrainmask;

    wmbrainmask_d = repmat(wmbrainmask,[1,1,1,dimt]);

    ctrldata_brain_wm = ctrldata;
    ctrldata_brain_wm(~wmbrainmask_d) = nan;
    labeldata_brain_wm = labeldata;
    labeldata_brain_wm(~wmbrainmask_d) = nan;
    diffdata_brain_wm = diffdata;
    diffdata_brain_wm(~wmbrainmask_d) = nan;

    mean_ctrl_brain_wm = validmean(ctrldata_brain_wm(:));
    mean_label_brain_wm = validmean(labeldata_brain_wm(:));
    mean_diff_brain_wm = validmean(diffdata_brain_wm(:));
    mean_diff_brain_wm_t = validmean(diffdata_brain_wm(:),1);

    negmask_brain_wm = diffdata_brain_wm < 0;
    diffdata_brain_wm_negsup = diffdata_brain_wm;
    diffdata_brain_wm_negsup(negmask_brain_wm) = nan;
    mean_diff_brain_wm_negsup = validmean(diffdata_brain_wm_negsup(:));

    perf_brain_wm = diffdata_brain_wm ./ ctrldata_brain_wm;
    mean_perf_brain_wm = validmean(perf_brain_wm);
    perf_brain_wm_negsup = diffdata_brain_wm_negsup ./ ctrldata_brain_wm;
    mean_perf_brain_wm_negsup = validmean(perf_brain_wm_negsup);

    snr_brain_wm = mean_diff_brain_wm/bg_std;
    snr_brain_wm_t = mean_diff_brain_wm_t ./ bg_std_t; 
    tsnr_brain_wm = mean(snr_brain_wm_t);

    cnr_brain = validmean(mean_diff_brain_gm - mean_diff_brain_wm) / bg_std;
    cnr_brain_t = (mean_diff_brain_gm_t - mean_diff_brain_wm_t) ./ bg_std_t;
    tcnr_brain = mean(cnr_brain_t);

    % csf mask metrics
    if isfile(csfmask_file)
        csfbrainii = niftiread(csfmask_file);
        csfbrainmask = csfbrainii > 0.5;
        aslmetrics(x).csfbrainmask = csfbrainmask;
    
        csfbrainmask_d = repmat(csfbrainmask,[1,1,1,dimt]);
    
        ctrldata_brain_csf = ctrldata;
        ctrldata_brain_csf(~csfbrainmask_d) = nan;
        labeldata_brain_csf = labeldata;
        labeldata_brain_csf(~csfbrainmask_d) = nan;
        diffdata_brain_csf = diffdata;
        diffdata_brain_csf(~csfbrainmask_d) = nan;
    
        mean_ctrl_brain_csf = validmean(ctrldata_brain_csf(:));
        mean_label_brain_csf = validmean(labeldata_brain_csf(:));
        mean_diff_brain_csf = validmean(diffdata_brain_csf(:));
    
        negmask_brain_csf = diffdata_brain_csf < 0;
        diffdata_brain_csf_negsup = diffdata_brain_csf;
        diffdata_brain_csf_negsup(negmask_brain_csf) = nan;
        mean_diff_brain_csf_negsup = validmean(diffdata_brain_csf_negsup(:));
    
        perf_brain_csf = diffdata_brain_csf ./ ctrldata_brain_csf;
        mean_perf_brain_csf = validmean(perf_brain_csf);
    
        perf_brain_csf_negsup = diffdata_brain_csf_negsup ./ ctrldata_brain_csf;
        mean_perf_brain_csf_negsup = validmean(perf_brain_csf_negsup);
    else    
        mean_ctrl_brain_csf = nan;
        mean_label_brain_csf = nan;
        mean_diff_brain_csf = nan;
        mean_diff_brain_csf_negsup = nan;
        mean_m0_brain_csf = nan;
        mean_perf_brain_csf = nan;
        mean_perf_brain_csf_negsup = nan;
        cgain_brain_csf = nan;
        mean_calib_brain_csf = nan;
        mean_calib_brain_csf_negsup = nan;
    end

    % M0
    mean_m0 = validmean(calibdata);

    sizectrl = size(calibdata);
    if length(sizectrl) > 3
        dimt = sizectrl(4);
        brainmask_calib_d = repmat(brainmask,[1,1,1,dimt]); 
        gmbrainmask_calib_d = repmat(gmbrainmask,[1,1,1,dimt]); 
        wmbrainmask_calib_d = repmat(wmbrainmask,[1,1,1,dimt]);
        if isfile(csfmask_file)
            csfbrainmask_calib_d = repmat(csfbrainmask,[1,1,1,dimt]); 
        end
    else
        brainmask_calib_d = brainmask;
        gmbrainmask_calib_d = gmbrainmask;
        wmbrainmask_calib_d = wmbrainmask;
        if isfile(csfmask_file)
            csfbrainmask_calib_d = csfbrainmask;
        end
    end
    
    calibdata_brain = calibdata;
    calibdata_brain(~brainmask_calib_d) = nan;
    mean_m0_brain = validmean(calibdata_brain);

    calibdata_brain_gm = calibdata;
    calibdata_brain_gm(~gmbrainmask_calib_d) = nan;
    mean_m0_brain_gm = validmean(calibdata_brain_gm);

    calibdata_brain_wm = calibdata;
    calibdata_brain_wm(~wmbrainmask_calib_d) = nan;
    mean_m0_brain_wm = validmean(calibdata_brain_wm);

    if isfile(csfmask_file)
        calibdata_brain_csf = calibdata;
        calibdata_brain_csf(~csfbrainmask_calib_d) = nan;
        mean_m0_brain_csf = validmean(calibdata_brain_csf);
    end

    if calibt > 1
        calibdata_mean = mean(calibdata,4);
        calibdata_brain_mean = mean(calibdata_brain,4);
        calibdata_brain_gm_mean = mean(calibdata_brain_gm,4);
        calibdata_brain_wm_mean = mean(calibdata_brain_wm,4);
        if isfile(csfmask_file)
            calibdata_brain_csf_mean = mean(calibdata_brain_csf,4);
        end
    else
        calibdata_mean = squeeze(calibdata);
        calibdata_brain_mean = squeeze(calibdata_brain);
        calibdata_brain_gm_mean = squeeze(calibdata_brain_gm);
        calibdata_brain_wm_mean = squeeze(calibdata_brain_wm);
        if isfile(csfmask_file)
            calibdata_brain_csf_mean = squeeze(calibdata_brain_csf); 
        end
    end

    ctrldata_mean = mean(ctrldata,4);
    ctrldata_brain_mean = mean(ctrldata_brain,4);
    ctrldata_brain_gm_mean = mean(ctrldata_brain_gm,4);
    ctrldata_brain_wm_mean = mean(ctrldata_brain_wm,4);
    if isfile(csfmask_file)
        ctrldata_brain_csf_mean = mean(ctrldata_brain_csf,4); 
    end

    aslnum=ctrldata_mean(~isnan(ctrldata_mean));
    calibnum=calibdata_mean(~isnan(ctrldata_mean));
    res = polyfit(aslnum, calibnum, 1);
    cgain = res(1);
    intercept = res(2);

    aslnum=ctrldata_brain_mean(~isnan(ctrldata_brain_mean));
    calibnum=calibdata_brain_mean(~isnan(ctrldata_brain_mean));
    res = polyfit(aslnum, calibnum, 1);
    cgain_brain = res(1);
    intercept_brain = res(2);

    aslnum=ctrldata_brain_gm_mean(~isnan(ctrldata_brain_gm_mean));
    calibnum=calibdata_brain_gm_mean(~isnan(ctrldata_brain_gm_mean));
    res = polyfit(aslnum, calibnum, 1);
    cgain_brain_gm = res(1);
    intercept_brain_gm = res(2);

    aslnum=ctrldata_brain_wm_mean(~isnan(ctrldata_brain_wm_mean));
    calibnum=calibdata_brain_wm_mean(~isnan(ctrldata_brain_wm_mean));
    res = polyfit(aslnum, calibnum, 1);
    cgain_brain_wm = res(1);
    intercept_brain_wm = res(2);
    
    if isfile(csfmask_file)
        aslnum=ctrldata_brain_csf_mean(~isnan(ctrldata_brain_csf_mean));
        calibnum=calibdata_brain_csf_mean(~isnan(ctrldata_brain_csf_mean));
        res = polyfit(aslnum, calibnum, 1);
        cgain_brain_csf = res(1);
        intercept_brain_csf = res(2);
    end
  
    mean_calib_mat = mean(diffdata,4) ./ calibdata_mean;
    mean_calib = validmean(mean_calib_mat);
    median_calib = validmedian(mean_calib_mat);

    mean_calib_negsup_mat = mean(diffdata_negsup,4) ./ calibdata_mean;
    mean_calib_negsup = validmean(mean_calib_negsup_mat);
    median_calib_negsup = validmedian(mean_calib_negsup_mat);

    mean_calib_brain_mat = mean(diffdata_brain,4) ./ calibdata_brain_mean;
    mean_calib_brain = validmean(mean_calib_brain_mat);
    median_calib_brain = validmedian(mean_calib_brain_mat);

    mean_calib_brain_negsup_mat = mean(diffdata_brain_negsup,4) ./ calibdata_brain_mean;
    mean_calib_brain_negsup = validmean(mean_calib_brain_negsup_mat);
    median_calib_brain_negsup = validmedian(mean_calib_brain_negsup_mat);

    mean_calib_brain_gm_mat = mean(diffdata_brain_gm,4) ./ calibdata_brain_gm_mean;
    mean_calib_brain_gm = validmean(mean_calib_brain_gm_mat);
    median_calib_brain_gm = validmedian(mean_calib_brain_gm_mat);

    mean_calib_brain_gm_negsup_mat = mean(diffdata_brain_gm_negsup,4) ./ calibdata_brain_gm_mean;
    mean_calib_brain_gm_negsup = validmean(mean_calib_brain_gm_negsup_mat);
    median_calib_brain_gm_negsup = validmedian(mean_calib_brain_gm_negsup_mat);

    mean_calib_brain_wm_mat = mean(diffdata_brain_wm,4) ./ calibdata_brain_wm_mean;
    mean_calib_brain_wm = validmean(mean_calib_brain_wm_mat);
    median_calib_brain_wm = validmedian(mean_calib_brain_wm_mat);

    mean_calib_brain_wm_negsup_mat = mean(diffdata_brain_wm_negsup,4) ./ calibdata_brain_wm_mean;
    mean_calib_brain_wm_negsup = validmean(mean_calib_brain_wm_negsup_mat);
    median_calib_brain_wm_negsup = validmedian(mean_calib_brain_wm_negsup_mat);

    if isfile(csfmask_file)
        mean_calib_brain_csf_mat = mean(diffdata_brain_csf,4) ./ calibdata_brain_csf_mean;
        mean_calib_brain_csf = validmean(mean_calib_brain_csf_mat);
        median_calib_brain_csf = validmedian(mean_calib_brain_csf_mat);
        
        mean_calib_brain_csf_negsup_mat = mean(diffdata_brain_csf_negsup,4) ./ calibdata_brain_csf_mean;
        mean_calib_brain_csf_negsup = validmean(mean_calib_brain_csf_negsup_mat);
        median_calib_brain_csf_negsup = validmedian(mean_calib_brain_csf_negsup_mat);
    end

    aslmetrics(x).neg_voxels_num=neg_voxels_num;
    aslmetrics(x).neg_voxels_mean=neg_voxels_mean;
    aslmetrics(x).neg_voxels_median=neg_voxels_median;
    aslmetrics(x).neg_voxels_peak=neg_voxels_peak;
    aslmetrics(x).neg_voxels_brain_num=neg_voxels_brain_num;
    aslmetrics(x).neg_voxels_brain_mean=neg_voxels_brain_mean;
    aslmetrics(x).neg_voxels_brain_median=neg_voxels_brain_median;
    aslmetrics(x).neg_voxels_brain_peak=neg_voxels_brain_peak;
    aslmetrics(x).mean_ctrl=mean_ctrl;
    aslmetrics(x).mean_label=mean_label;
    aslmetrics(x).mean_diff=mean_diff;
    aslmetrics(x).mean_diff_negsup=mean_diff_negsup;
    aslmetrics(x).mean_ctrl_brain=mean_ctrl_brain;
    aslmetrics(x).mean_label_brain=mean_label_brain;
    aslmetrics(x).mean_diff_brain=mean_diff_brain;
    aslmetrics(x).mean_diff_brain_negsup=mean_diff_brain_negsup;
    aslmetrics(x).mean_ctrl_brain_gm=mean_ctrl_brain_gm;
    aslmetrics(x).mean_label_brain_gm=mean_label_brain_gm;
    aslmetrics(x).mean_diff_brain_gm=mean_diff_brain_gm;
    aslmetrics(x).mean_diff_brain_gm_negsup=mean_diff_brain_gm_negsup;
    aslmetrics(x).mean_ctrl_brain_wm=mean_ctrl_brain_wm;
    aslmetrics(x).mean_label_brain_wm=mean_label_brain_wm;
    aslmetrics(x).mean_diff_brain_wm=mean_diff_brain_wm;
    aslmetrics(x).mean_diff_brain_wm_negsup=mean_diff_brain_wm_negsup;
    aslmetrics(x).mean_ctrl_brain_csf=mean_ctrl_brain_csf;
    aslmetrics(x).mean_label_brain_csf=mean_label_brain_csf;
    aslmetrics(x).mean_diff_brain_csf=mean_diff_brain_csf;
    aslmetrics(x).mean_diff_brain_csf_negsup=mean_diff_brain_csf_negsup;
    aslmetrics(x).mean_m0=mean_m0;
    aslmetrics(x).mean_m0_brain=mean_m0_brain;
    aslmetrics(x).mean_m0_brain_gm=mean_m0_brain_gm;
    aslmetrics(x).mean_m0_brain_wm=mean_m0_brain_wm;
    aslmetrics(x).mean_m0_brain_csf=mean_m0_brain_csf;
    aslmetrics(x).mean_perf=mean_perf;
    aslmetrics(x).median_perf=median_perf;
    aslmetrics(x).mean_perf_negsup=mean_perf_negsup;
    aslmetrics(x).median_perf_negsup=median_perf_negsup;
    aslmetrics(x).mean_perf_brain=mean_perf_brain;
    aslmetrics(x).median_perf_brain=median_perf_brain;
    aslmetrics(x).mean_perf_brain_negsup=mean_perf_brain_negsup;
    aslmetrics(x).median_perf_brain_negsup=median_perf_brain_negsup;
    aslmetrics(x).mean_perf_brain_gm=mean_perf_brain_gm;
    aslmetrics(x).mean_perf_brain_gm_negsup=mean_perf_brain_gm_negsup;
    aslmetrics(x).mean_perf_brain_wm=mean_perf_brain_wm;
    aslmetrics(x).mean_perf_brain_wm_negsup=mean_perf_brain_wm_negsup;
    aslmetrics(x).mean_perf_brain_csf=mean_perf_brain_csf;
    aslmetrics(x).mean_perf_brain_csf_negsup=mean_perf_brain_csf_negsup;
    aslmetrics(x).cgain=cgain;
    aslmetrics(x).cgain_brain=cgain_brain;
    aslmetrics(x).cgain_brain_gm=cgain_brain_gm;
    aslmetrics(x).cgain_brain_wm=cgain_brain_wm;
    aslmetrics(x).cgain_brain_csf=cgain_brain_csf;
    aslmetrics(x).mean_calib=mean_calib;
    aslmetrics(x).mean_calib_negsup=mean_calib_negsup;
    aslmetrics(x).mean_calib_brain=mean_calib_brain;
    aslmetrics(x).mean_calib_brain_negsup=mean_calib_brain_negsup;
    aslmetrics(x).median_calib=median_calib;
    aslmetrics(x).median_calib_negsup=median_calib_negsup;
    aslmetrics(x).median_calib_brain=median_calib_brain;
    aslmetrics(x).median_calib_brain_negsup=median_calib_brain_negsup;
    aslmetrics(x).mean_calib_brain_gm=mean_calib_brain_gm;
    aslmetrics(x).mean_calib_brain_gm_negsup=mean_calib_brain_gm_negsup;
    aslmetrics(x).mean_calib_brain_wm=mean_calib_brain_wm;
    aslmetrics(x).mean_calib_brain_wm_negsup=mean_calib_brain_wm_negsup;
    aslmetrics(x).mean_calib_brain_csf=mean_calib_brain_csf;
    aslmetrics(x).mean_calib_brain_csf_negsup=mean_calib_brain_csf_negsup;
    aslmetrics(x).snr_brain_gm=snr_brain_gm;
    aslmetrics(x).snr_brain_gm_t=snr_brain_gm_t;
    aslmetrics(x).tsnr_brain_gm=tsnr_brain_gm;
    aslmetrics(x).snr_brain_wm=snr_brain_wm;
    aslmetrics(x).snr_brain_wm_t=snr_brain_wm_t;
    aslmetrics(x).tsnr_brain_wm=tsnr_brain_wm;
    aslmetrics(x).cnr_brain=cnr_brain;
    aslmetrics(x).cnr_brain_t=cnr_brain_t; 
    aslmetrics(x).tcnr_brain=tcnr_brain;
end

Variables = [ 
"subject_id","session_id","sitehr","acq"...    
"neg_voxels_num",...
"neg_voxels_mean",...
"neg_voxels_median",...
"neg_voxels_peak",...
"neg_voxels_brain_num",...
"neg_voxels_brain_mean",...
"neg_voxels_brain_median",...
"neg_voxels_brain_peak",...
"mean_ctrl",...
"mean_label",...
"mean_diff",...
"mean_diff_negsup",...
"mean_ctrl_brain",...
"mean_label_brain",...
"mean_diff_brain",...
"mean_diff_brain_negsup",...
"mean_ctrl_brain_gm",...
"mean_label_brain_gm",...
"mean_diff_brain_gm",...
"mean_diff_brain_gm_negsup",...
"mean_ctrl_brain_wm",...
"mean_label_brain_wm",...
"mean_diff_brain_wm",...
"mean_diff_brain_wm_negsup",...
"mean_ctrl_brain_csf",...
"mean_label_brain_csf",...
"mean_diff_brain_csf",...
"mean_diff_brain_csf_negsup",...
"mean_m0",...
"mean_m0_brain",...
"mean_m0_brain_gm",...
"mean_m0_brain_wm",...
"mean_m0_brain_csf",...
"mean_perf",...
"median_perf",...
"mean_perf_negsup",...
"median_perf_negsup",...
"mean_perf_brain",...
"median_perf_brain",...
"mean_perf_brain_negsup",...
"median_perf_brain_negsup",...
"mean_perf_brain_gm",...
"mean_perf_brain_gm_negsup",...
"mean_perf_brain_wm",...
"mean_perf_brain_wm_negsup",...
"mean_perf_brain_csf",...
"mean_perf_brain_csf_negsup",...
"cgain",...
"cgain_brain",...
"cgain_brain_gm",...
"cgain_brain_wm",...
"cgain_brain_csf",...
"mean_calib",...
"mean_calib_negsup",...
"mean_calib_brain",...
"mean_calib_brain_negsup",...
"median_calib",...
"median_calib_negsup",...
"median_calib_brain",...
"median_calib_brain_negsup",...
"mean_calib_brain_gm",...
"mean_calib_brain_gm_negsup",...
"mean_calib_brain_wm",...
"mean_calib_brain_wm_negsup",...
"mean_calib_brain_csf",...
"mean_calib_brain_csf_negsup",...
"snr_brain_gm",...
"tsnr_brain_gm",...
"snr_brain_wm",...
"tsnr_brain_wm",...
"cnr_brain",...
"tcnr_brain"
];
OUT = createTable(aslmetrics,Variables);
writetable(OUT,csvout)