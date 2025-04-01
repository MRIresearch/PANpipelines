import amico
import os
import nibabel
import json
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from functools import partial
import logging
import sys

loglevel=logging.INFO
LOGGER = logging.getLogger("amico")
LOGGER.setLevel(loglevel)
formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(loglevel)
stdout_handler.setFormatter(formatter)
LOGGER.addHandler(stdout_handler)

def run_amico(participant, session, qsiprep_dir, output_path=None,path_suffix="",amico_model=None,model_config=None,amico_config = None, labels_dict={}):
    qsiprep_in=os.path.join(qsiprep_dir,f"sub-{participant}")
    bval = os.path.join(qsiprep_in,f"ses-{session}","dwi",f"sub-{participant}_ses-{session}_space-T1w_desc-preproc_dwi.bval")
    bvec = os.path.join(qsiprep_in,f"ses-{session}","dwi",f"sub-{participant}_ses-{session}_space-T1w_desc-preproc_dwi.bvec")
    dwi = os.path.join(qsiprep_in,f"ses-{session}","dwi",f"sub-{participant}_ses-{session}_space-T1w_desc-preproc_dwi.nii.gz")
    mask = os.path.join(qsiprep_in,f"ses-{session}","dwi",f"sub-{participant}_ses-{session}_space-T1w_desc-brain_mask.nii.gz")

    amico.setup()
    ae = amico.Evaluation(output_path=output_path)

    if amico_config:
        with open(amico_config,"r") as infile:
            amico_config_json = json.load(infile)
        if amico_config_json:
            for itemkey,itemvalue in amico_config_json:
                ae.set_config(itemkey,itemvalue)

    ae.set_model(amico_model)
    if amico_model == 'NODDI':
        LOGGER.info(f"Running Amico Model:\n{amico_model}")
        scheme = amico.util.fsl2scheme(bval, bvec)

        ae.load_data(dwi, scheme, mask, b0_thr=2)

        if model_config:
            with open(model_config,"r") as infile:
                model_config_json = json.load(infile)

            if model_config_json:
                if "dPar" in model_config_json.keys():
                    ae.model.dPar= model_config_json["dPar"]
                if "dIso" in model_config_json.keys():
                    ae.model.dIso=model_config_json["dIso"]
                if "IC_VFs" in model_config_json.keys():
                    ae.model.dIso=model_config_json["IC_VFs"]
                if "IC_ODs" in model_config_json.keys():
                    ae.model.dIso=model_config_json["IC_ODs"]
                if "isExvivo" in model_config_json.keys():
                    ae.model.dIso=model_config_json["isExvivo"]

        model_params = ae.model.get_params()
        LOGGER.info(f"model parameters:\n{model_params}")
        ae.generate_kernels(regenerate=True)
        ae.load_kernels()
        ae.fit()
        ae.save_results(path_suffix=path_suffix)

def parse_params():
    parser = ArgumentParser(description="amico")
    parser.add_argument("--participant", help="BIDS Participant label")
    parser.add_argument("--session", help="BIDS Session label")
    parser.add_argument("--qsiprep_dir", type=Path,  help="Input qsiprep directory")
    parser.add_argument("--amico_model", help="Amico model to run", default="NODDI")
    parser.add_argument("--path_suffix", help="path suffix")
    parser.add_argument("--model_config", type=Path, help="Model config json")
    parser.add_argument("--amico_config", type=Path, help="AMICO configuration json")
    parser.add_argument("--output_path", type=Path, help="Output results")
    parser.add_argument("--pipeline_config_file", type=Path, help="Pipeline Config File")
    return parser

def main():
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()
    participant = args.participant
    session = args.session
    amico_model = args.amico_model
    path_suffix = args.path_suffix
    qsiprep_dir = args.qsiprep_dir
    model_config = args.model_config
    amico_config = args.amico_config
    output_path = args.output_path

    if not output_path:
        output_path=os.path.join(os.getcwd,"amico_out")

    if not os.path.exists(output_path):
        os.makedirs(output_path,exist_ok=True)

    pipeline_config_file = None
    if args.pipeline_config_file:
        if Path(args.pipeline_config_file).exists():
            pipeline_config_file = str(args.pipeline_config_file)

    labels_dict={}
    if pipeline_config_file:
        panpipeconfig_file=str(pipeline_config_file)
        if os.path.exists(pipeline_config_file):
           print(f"{pipeline_config_file} exists.")
           with open(pipeline_config_file,'r') as infile:
               labels_dict = json.load(infile)

    run_amico(participant, session, qsiprep_dir, output_path=output_path, amico_model=amico_model, path_suffix=path_suffix, model_config=model_config,amico_config = amico_config,labels_dict=labels_dict)

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()