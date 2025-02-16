from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import dominate
from dominate.tags import *
from nipype import logging as nlogging
from nilearn import plotting
from bs4 import BeautifulSoup

def guess_type(filepath):
    """
    Return the mimetype of a file, given it's path.

    This is a wrapper around two alternative methods - Unix 'file'-style
    magic which guesses the type based on file content (if available),
    and simple guessing based on the file extension (eg .jpg).

    :param filepath: Path to the file.
    :type filepath: str
    :return: Mimetype string.
    :rtype: str
    """
    try:
        import magic  # python-magic
        return magic.from_file(filepath, mime=True)
    except ImportError:
        import mimetypes
        return mimetypes.guess_type(filepath)[0]

def file_to_base64(filepath):
    """
    Returns the content of a file as a Base64 encoded string.

    :param filepath: Path to the file.
    :type filepath: str
    :return: The file content, Base64 encoded.
    :rtype: str
    """
    import base64
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            encoded_str = base64.b64encode(f.read())
        return encoded_str.decode('utf-8')
    else:
        return "error: image not located"


def make_html_images_inline(in_filepath, out_filepath):
    """
    Takes an HTML file and writes a new version with inline Base64 encoded
    images.

    :param in_filepath: Input file path (HTML)
    :type in_filepath: str
    :param out_filepath: Output file path (HTML)
    :type out_filepath: str
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    soup = BeautifulSoup(open(in_filepath, 'r'), 'html.parser')

    # add 
    new_style = soup.new_tag('style')
    new_style.attrs['type']="text/css"

    for head in soup.find_all('head'):
        for link in head.find_all('link'):
            if link.has_attr("rel"):
                if link["rel"][0] == "stylesheet":
                    if link.has_attr("href"):
                        styleref = link["href"]
                        if os.path.exists(styleref):
                            with open(styleref, 'r') as fileid:
                                styletext=fileid.read()
                            styletext = styletext.replace('\t','').replace('\n','')
                            link.decompose()
                            new_style.string = styletext
                            head.append(new_style)


    for img in soup.find_all('img'):
        img_path = os.path.join(basepath, img.attrs['src'])
        mimetype = guess_type(img_path)
        img.attrs['src'] = \
            "data:%s;base64,%s" % (mimetype, file_to_base64(img_path))

    for obj in soup.find_all('object'):
        if obj.has_attr('type') and obj.has_attr('data'):
            if obj["type"] == "image/svg+xml":
                svgdata_file=obj["data"]
                if os.path.exists(svgdata_file):
                    with open(svgdata_file,'r') as infile:
                        svgdata=infile.read()
                    svgclean=svgdata.replace('\n','').replace('\t','').replace('"',"'")
                    #svgclean="<img src=\"image/svg+xml;utf8,"+svgclean + "\"></img>"
                    #new_img = soup.new_tag('img')
                    #new_img.attrs['src']="image/svg+xml;utf8,{}".format(BeautifulSoup(svgclean,'html.parser'))
                    obj.insert_after(BeautifulSoup(svgclean,'html.parser'))
                    #obj.insert_after(new_img)
                    obj.decompose()
            elif obj["type"] == "image/gif":
                svgdata_file=obj["data"]
                if os.path.exists(svgdata_file):
                    mimetype = guess_type(svgdata_file)
                    new_img = soup.new_tag('img')
                    new_img.attrs['src'] = "data:%s;base64,%s" % (mimetype, file_to_base64(svgdata_file))
                    obj.insert_after(new_img)
                    obj.decompose()
                        

    for svgobj in soup.find_all('svg'):
        svgobj.attrs["class"] = "svg-reportlet"

    allsoup=str(soup)

    with open(out_filepath, 'w') as of:
        of.write(str(allsoup))

def create_document(title, stylesheet=None, script=None):
    doc = dominate.document(title = title)
    if stylesheet is not None:
        with doc.head:
            link(rel='stylesheet',href=stylesheet)
    if script is not None:
        with doc.head:
            script(type='text/javascript',src=script)
    with doc:
        with div(id='header',cls="header"):
            h1(title)
        with div(id='timestamp',cls="header_timestamp"):
            p('Report generated on {}'.format(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')) )
    return doc

def create_section(doc, divid, divclass, captiontext):
    with doc:
        if divclass is None:
            d = div(id=divid)
        else:
            d = div(id=divid, cls=divclass)
        with d:
            h2(captiontext)
    return doc


def create_table(doc, divid, divclass, tabid, tabclass, headers, captiontext, reportlist):
    with doc:
        if divclass is None:
            d = div(id=divid)
        else:
            d = div(id=divid, cls=divclass)
        with d:
            h3(captiontext)
            if tabclass is None:
                t = table(id = tabid)
            else:
                t = table(id = tabid, cls = tabclass)
            with t:
                with thead():
                    with tr():
                        for header in headers:
                            th(header)
                with tbody():
                    for listitem in reportlist:
                        with tr():
                            for itemvalue  in listitem:
                                td(itemvalue)
    return doc

def create_float_table(tabid, tabclass, headers, reportlist):
    if tabclass is None:
        t = table(id = tabid)
    else:
        t = table(id = tabid, cls = tabclass)
    with t:
        with thead():
            with tr():
                for header in headers:
                    th(header)
        with tbody():
            for listitem in reportlist:
                with tr():
                    for itemvalue  in listitem:
                        td(itemvalue)
    return t

def add_image(doc, divid, divclass, captiontext, image):
    with doc:
        if divclass is None:
            d = div(id=divid)
        else:
            d = div(id=divid, cls=divclass)
        with d:
            h3(captiontext)
            img(src=image)
    return doc

def add_float_image(imgid, imgclass, image):
    if imgclass is None:
        m = img(id=imgid, src=image)
    else:
        m = img(id=imgid, cls=imgclass, src=image)

    return m



def formatDateTime(row, fmt):
    dt = datetime.datetime.strptime(row['datetime'],'%Y-%m-%dT%H:%M:%S.%f')
    return datetime.datetime.strftime(dt, fmt)

def returnAverage(row):
    if len(str(row['value']).split(',')) > 1:
        row_values= [float(x) for x in row['value'].replace('[','').replace(']','').replace(' ','').split(',')]
        return np.mean(np.asarray(row_values))
    else:
        return row['value']


def writeROIimage(mask_rois, threeDfile, image ):
    combo = None
    for roi in mask_rois:
        roiimg = nib.load(roi)
        roidata = roiimg.get_fdata()
        if combo is None:
            combo = roidata
            combo_affine = roiimg.affine
            combo_header = roiimg.header
        else:
            combo=np.add(combo,roidata)

    funcimg = nib.load(threeDfile)
    if len(funcimg.header.get_data_shape()) > 3:
        funclist = nib.funcs.four_to_three(funcimg)
        threeDfile = funclist[0]

    combo_img = nib.Nifti1Image(combo, combo_affine, combo_header)

    display=plotting.plot_roi(combo_img, bg_img=threeDfile)
    display.savefig(image)


def writeStatImage(threeDfile, image, dmode='ortho'):
    display=plotting.plot_stat_map(threeDfile, display_mode=dmode)
    display.savefig(image)


def createRegisteredImage(image_list,image_png, only_first = False, bg_image_file = None, levellist=[0.5],colors=['r','g','b','y','m','c'],roi_index=None):

    contour_list=[]
    for image_file in image_list:
        contour_img = nib.load(image_file)
        if len(contour_img.header.get_data_shape()) > 3:
            expand_img = nib.funcs.four_to_three(contour_img)
            if only_first:
                contour_list.append(expand_img[0])
            else:
                contour_list.extend(expand_img)
        else:
            contour_list.append(contour_img)

    bg_img = None
    contours = []
    if bg_image_file:
        bg_img = nib.load(bg_image_file)
        contours = contour_list
        if roi_index:
            roi_index = min(roi_index,len(contour_list) - 1)
    else:
        if contour_list:
            bg_img = contour_list[0]
            if len(contour_list) > 1:
                contours = contour_list[1:]
                if roi_index:
                    roi_index = min(roi_index,len(contours) - 1)
            else:
                roi_index = None
        else:
            roi_index=None

    if bg_img:
        writeContourImages(bg_img,contours, image_png, levellist=levellist,colors=colors,roi_index=roi_index)
    else:
        print("Error - no image files provided")

            
def writeContourImages(bg_img,contours, png_file, levellist=[0.5],colors=['r','g','b','y','m','c'],roi_index=None):
        if roi_index is not None:
            mycanvas=plotting.plot_roi(contours[roi_index], bg_img=bg_img)
        else:
            mycanvas=plotting.plot_anat(bg_img)
        colorcount=0
        colorsize=len(colors)
        for contour_img in contours:
            colornum=colorcount%colorsize
            mycanvas.add_contours(contour_img,levels=levellist,colors=colors[colornum])
            colorcount=colorcount+1
      
        if not os.path.exists(os.path.dirname(png_file)):
            os.makedirs(os.path.dirname(png_file),exist_ok=True)
        mycanvas.savefig(png_file)
    

def AddDataSection(doc, doc_dict):

    headers = doc_dict["headers"]
    rows = doc_dict["rows"]
    title = doc_dict["title"]
    divid = doc_dict["divid"]

    if "tabid" in doc_dict.keys():
        tabid = doc_dict["tabid"]
    else:
        tabid = divid

    if "tabclass" in doc_dict.keys():
        tabclass = doc_dict["tabclass"]
    else:
        tabclass = None

    if "divclass" in doc_dict.keys():
        divclass = doc_dict["divclass"]
    else:
        divclass = None

    doc = create_table(doc, divid, divclass, tabid, tabclass, headers, title, rows)

    return doc

def AddRegSection(doc,doc_dict,only_first = False, bg_image_file = None, levellist=[0.5],colors=['r','g','b','y','m','c'],roi_index=None):

    image_list = doc_dict["image_list"]
    image_png = doc_dict["image_png"]
    title = doc_dict["title"]
    divid = doc_dict["divid"]

    if "divclass" in doc_dict.keys():
        divclass = doc_dict["divclass"]
    else:
        divclass = None

    createRegisteredImage(image_list,image_png,only_first = only_first, bg_image_file = bg_image_file, levellist=levellist,colors=colors,roi_index=roi_index)

    doc = add_image(doc, divid, divclass, title, image_png)

    return doc


def addRoiExtractProcReport(doc_dict):

    stylesheet = doc_dict["stylesheet"]
    title = doc_dict["title"]
    image_dir = doc_dict["image_dir"]
    output_dir = doc_dict["output_dir"] 
    mask = doc_dict["mask"] 
    atlas = doc_dict["atlas"] 
    measure = doc_dict["measure"]
    pipeline = doc_dict["pipeline"]
    metadata = doc_dict["metadata"]

    doc = create_document(title, stylesheet)
    with doc:
        with div(id='links',cls='contents').add(ul()):
            h2('Contents')
            li(a('Measure Registration',href='#measureregistration'))
            nested=ul()
            with nested:
                if mask:
                    for i in ['mask_measure', 'atlas_measure','mask_atlas_measure']:
                        li(a(i.title(), href='#%s' % i))
                else:
                    for i in ['atlas_measure']:
                        li(a(i.title(), href='#%s' % i))

            li(a('Measures Info',href='#measuresinfo'))
            nested=ul()
            with nested:
                for i in ['measures_table', 'roi_sizes_table','roi_coverage','measures_metadata']:
                    li(a(i.title(), href='#%s' % i))

    doc += hr()
    doc = create_section(doc, 'measureregistration', 'section', f"Registration")
    doc += hr()

    if mask:
        reg1_dict={}
        reg1_dict["image_list"] = [measure,mask]
        reg1_dict["image_png"] = os.path.join(image_dir,'mask_measure.png')
        reg1_dict["title"] = 'mask overlayed on measure'
        reg1_dict["divid"] = 'mask_measure'
        reg1_dict["divclass"] = 'img-caption'
        doc = AddRegSection(doc, reg1_dict,levellist=[0.5,5,10,15])
        doc += hr()

    reg1_dict={}
    reg1_dict["image_list"] = [measure,atlas]
    reg1_dict["image_png"] = os.path.join(image_dir,'atlas_measure.png')
    reg1_dict["title"] = 'atlas overlayed on measure'
    reg1_dict["divid"] = 'atlas_measure'
    reg1_dict["divclass"] = 'img-caption'
    doc = AddRegSection(doc, reg1_dict,levellist=[0.5,5,10,15],colors = ['g','b','y','m','c'],roi_index=0)
    doc += hr()

    if mask:
        reg1_dict={}
        reg1_dict["image_list"] = [measure,mask,atlas]
        reg1_dict["image_png"] = os.path.join(image_dir,'mask_atlas_measure.png')
        reg1_dict["title"] = 'mask overlaid on atlas and measure'
        reg1_dict["divid"] = 'mask_atlas_measure'
        reg1_dict["divclass"] = 'img-caption'
        doc = AddRegSection(doc, reg1_dict,levellist=[0.5,5,10,15],roi_index=1)
        doc += hr()


    doc += hr()
    doc = create_section(doc, 'measuresinfo', 'section', f"Measures Information")
    doc += hr()

    reg1_dict={}
    measures_table = metadata["FileCreated"]
    df = pd.read_table(measures_table,sep=",")
    reg1_dict["headers"] = df.columns.tolist()
    reg1_dict["rows"] = df.values.tolist()
    reg1_dict["title"] = "Measures"
    reg1_dict["divid"] = 'measures_table'
    reg1_dict["tabclass"] = 'data-table'
    reg1_dict["divclass"] = 'table-caption'
    doc = AddDataSection(doc, reg1_dict)
    doc += hr()

    reg1_dict={}
    roi_sizes_table = metadata["ROI Voxel Sizes"]
    df = pd.read_table(roi_sizes_table,sep=",")
    reg1_dict["headers"] = df.columns.tolist()
    reg1_dict["rows"] = df.values.tolist()
    reg1_dict["title"] = "ROI Voxel Sizes"
    reg1_dict["divid"] = 'roi_sizes_table'
    reg1_dict["tabclass"] = 'data-table'
    reg1_dict["divclass"] = 'table-caption'
    doc = AddDataSection(doc, reg1_dict)
    doc += hr()

    reg1_dict={}
    roi_sizes_table = metadata["ROI Coverage"]
    df = pd.read_table(roi_sizes_table,sep=",")
    reg1_dict["headers"] = df.columns.tolist()
    reg1_dict["rows"] = df.values.tolist()
    reg1_dict["title"] = "ROI Coverage"
    reg1_dict["divid"] = 'roi_coverage_table'
    reg1_dict["tabclass"] = 'data-table'
    reg1_dict["divclass"] = 'table-caption'
    doc = AddDataSection(doc, reg1_dict)
    doc += hr()

    reg1_dict={}
    reg1_dict["headers"] = ["Item", "Value"]
    reg1_dict["rows"] = [[k,metadata[k]] for k in metadata.keys()]
    reg1_dict["title"] = "Metadata"
    reg1_dict["divid"] = 'measures_metadata'
    reg1_dict["tabclass"] = 'info-table'
    reg1_dict["divclass"] = 'table-caption'
    doc = AddDataSection(doc, reg1_dict)
    doc += hr()

    return doc

def createRoiExtractReport(panpipe_labels,html_file, metadata,analysis_level=None):
    stylesheet = getParams(panpipe_labels,"STYLESHEET")
    pipeline = getParams(panpipe_labels,"PIPELINE")

    report_title = f"Html report for {pipeline}"
    if analysis_level == "participant":
        participant = getParams(panpipe_labels,"PARTICIPANT_LABEL")
        session = getParams(panpipe_labels,"PARTICIPANT_SESSION")
        report_title = f"Subject {participant}, Session {session} : " + report_title

    output_dir = os.path.dirname(html_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    if isinstance(metadata,dict):
        metajson = metadata
    else:
        with open(metadata,"r") as infile:
            metajson = json.load(infile)

    image_dir=os.path.join(output_dir, 'images')

    doc_dict={}
    doc_dict["title"] = report_title
    doc_dict["stylesheet"] = f"{stylesheet}"
    doc_dict["image_dir"] = f"{image_dir}"
    doc_dict["output_dir"] = f"{output_dir}"
    if "Mask" in metajson.keys():
        doc_dict["mask"] = metajson["Mask"]
    else:
        doc_dict["mask"] = ""
    doc_dict["atlas"] = metajson["Atlas File"]
    doc_dict["measure"] = metajson["Input File"]
    doc_dict["pipeline"] = f"{pipeline}"
    doc_dict["metadata"] = metajson

    doc = addRoiExtractProcReport(doc_dict)

    html_file = newfile(assocfile=html_file,extension="html")
    html_file_working = newfile(assocfile=html_file,suffix="working")
    with open(html_file_working, 'w') as file:
        file.write(doc.render())
    make_html_images_inline(html_file_working, html_file)

    return html_file 


def addBasilMotionSection(doc,doc_dict):

    image_dir = doc_dict["image_dir"]
    debug_dir = doc_dict["debug_dir"] 
    fsl_tsplot=doc_dict["command_base"] + ' fsl_tsplot '

    #asldatapre=os.path.join(debug_dir,'asldata_orig.nii.gz')
    #image1=os.path.join(image_dir,'asldatapre.png')
    #asldatapost=os.path.join(debug_dir,'asldata.nii.gz')
    #image2=os.path.join(image_dir,'asldatapost.png')

    #reg1_dict={}
    #reg1_dict["image_list"] = [asldatapre]
    #reg1_dict["image_png"] = image1
    #reg1_dict["title"] = 'asldata before motion correction'
    #reg1_dict["divid"] = 'asldata_pre'
    #reg1_dict["divclass"] = 'img-caption'
    #doc = AddRegSection(doc, reg1_dict,levellist=[0.5,5,10,15])
    #doc += hr()

    #reg1_dict={}
    #reg1_dict["image_list"] = [asldatapost]
    #reg1_dict["image_png"] = image2
    #reg1_dict["divid"] = 'asldata_post'
    #reg1_dict["divclass"] = 'img-caption'
    #doc = AddRegSection(doc, reg1_dict,levellist=[0.5,5,10,15])
    #doc += hr()
    
    asldatapar=os.path.join(debug_dir,'asldata.par')
    image3=os.path.join(image_dir,'rot.png')
    fsl_tsplot_rot_command="{} -i {}  -t {} -u 1 --start=1 --finish=3 -a x,y,z -w 640 -h 144 -o {}".format(fsl_tsplot,asldatapar,'MCFLIRT_estimated_rotations_radians',image3)
    results = runCommand(fsl_tsplot_rot_command,UTLOGGER)
    doc = add_image(doc, "rotations", None, 'Rotation', image3)

    image4=os.path.join(image_dir,'trans.png')
    fsl_tsplot_trans_command="{} -i {}  -t {} -u 1 --start=4 --finish=6 -a x,y,z -w 640 -h 144 -o {}".format(fsl_tsplot,asldatapar,'MCFLIRT_estimated_translations_mm',image4)
    results = runCommand(fsl_tsplot_trans_command,UTLOGGER)
    doc = add_image(doc, "translations", None, 'Translation', image4)

    return doc


def addBasilStructRegSection(doc,doc_dict):

    title = doc_dict["title"]
    image_dir = doc_dict["image_dir"]
    debug_dir = doc_dict["debug_dir"] 

    struct=os.path.join(debug_dir,'struc.nii.gz')
    struct_bet_mask=os.path.join(debug_dir,'struc_bet_mask.nii.gz')
    image1=os.path.join(image_dir,'structmask_struct.png')
    calib=os.path.join(debug_dir,'calib_struc.nii.gz')
    image2=os.path.join(image_dir,'structmask_calib.png')
    asl=os.path.join(debug_dir,'asl2struct.nii.gz')
    image3=os.path.join(image_dir,'asl_struct.png')
    image4=os.path.join(image_dir,'asl_calib.png')

    reg1_dict={}
    reg1_dict["image_list"] = [struct,struct_bet_mask]
    reg1_dict["image_png"] = image1
    reg1_dict["title"] = 'brain mask overlaid on structural'
    reg1_dict["divid"] = 'structmask_struct'
    reg1_dict["divclass"] = 'img-caption'
    doc = AddRegSection(doc, reg1_dict,only_first = True,levellist=[0.5,5,10,15])
    doc += hr()

    reg1_dict={}
    reg1_dict["image_list"] = [calib,struct_bet_mask]
    reg1_dict["image_png"] = image2
    reg1_dict["title"] = 'brain mask overlaid on calibration image'
    reg1_dict["divid"] = 'structmask_calib'
    reg1_dict["divclass"] = 'img-caption'
    doc = AddRegSection(doc, reg1_dict,only_first = True,levellist=[0.5,5,10,15])
    doc += hr()

    reg1_dict={}
    reg1_dict["image_list"] = [struct,asl]
    reg1_dict["image_png"] = image3
    reg1_dict["title"] = 'asl overlaid on structural image'
    reg1_dict["divid"] = 'asl_struct'
    reg1_dict["divclass"] = 'img-caption'
    doc = AddRegSection(doc, reg1_dict,only_first = True,levellist=[0.5,5,10,15])
    doc += hr()

    reg1_dict={}
    reg1_dict["image_list"] = [calib,asl]
    reg1_dict["image_png"] = image4
    reg1_dict["title"] = 'asl overlaid on calib image'
    reg1_dict["divid"] = 'asl_calib'
    reg1_dict["divclass"] = 'img-caption'
    doc = AddRegSection(doc, reg1_dict,only_first = True,levellist=[0.5,5,10,15])
    doc += hr()

    return doc

def addBasilProcReport(doc_dict):
    stylesheet = doc_dict["stylesheet"]
    title = doc_dict["title"]

    doc = create_document(title, stylesheet)
    with doc:
        with div(id='links').add(ul()):
            h2('Contents')
            li(a('Structural Registration',href='#structuralreg'))
            nested=ul()
            with nested:
                for i in ['structmask_struct', 'structmask_calib','asl_struct','asl_calib']:
                    li(a(i.title(), href='#%s' % i))
            li(a('Motion Correction',href='#motioncorrection'))
            nested=ul()
            with nested:
                #for i in [ 'asldata_pre', 'asldata_post','rotations','translations']:
                for i in ['rotations','translations']:
                    li(a(i.title(), href='#%s' % i))

    doc += hr()
    doc = create_section(doc, 'structuralreg', None, 'Structural Registration')
    doc += hr()
    doc = addBasilStructRegSection(doc, doc_dict)
    doc += hr()
    doc = create_section(doc, 'motioncorrection', None, 'Motion Correction')
    doc += hr()
    doc = addBasilMotionSection(doc, doc_dict)

    return doc


def createBasilReport(panpipe_labels,html_file,debug_dir,analysis_level=None):
    stylesheet = getParams(panpipe_labels,"STYLESHEET")
    pipeline = getParams(panpipe_labels,"PIPELINE")
    report_title = f"Html report for {pipeline}"

    if analysis_level == "participant":
        participant = getParams(panpipe_labels,"PARTICIPANT_LABEL")
        session = getParams(panpipe_labels,"PARTICIPANT_SESSION")
        report_title = f"Subject {participant}, Session {session} : " + report_title

    output_dir = os.path.dirname(html_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    image_dir=os.path.join(output_dir, 'images')

    doc_dict={}
    doc_dict["title"] = report_title
    doc_dict["stylesheet"] = f"{stylesheet}"
    doc_dict["image_dir"] = f"{image_dir}"
    doc_dict["output_dir"] = f"{output_dir}"
    doc_dict["debug_dir"] = debug_dir
    doc_dict["pipeline"] = f"{pipeline}"
    doc_dict["command_base"] = substitute_labels("<PAN_CONTAINER_RUN_OPTIONS> <PAN_CONTAINER> ",panpipe_labels)

    doc = addBasilProcReport(doc_dict)

    html_file = newfile(assocfile=html_file,extension="html")
    html_file_working = newfile(assocfile=html_file,suffix="working")
    with open(html_file_working, 'w') as file:
        file.write(doc.render())
    make_html_images_inline(html_file_working, html_file)

    return html_file 




