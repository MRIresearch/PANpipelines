from sdcflows import fieldmaps as sfm
from nipype import Workflow, Node
from nipype.interfaces.io import DataSink
from nipype import logging as nlogging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from functools import partial
import os

IFLOGGER=nlogging.getLogger('nipype.interface')


def parse_params():
    parser = ArgumentParser(description="SDCflows fieldmap workflow")
    parser.add_argument("--fmap_sources", nargs="+", help="Fmap sources")
    parser.add_argument("--subject", help="Subject")
    parser.add_argument("--session", help="Session")
    parser.add_argument("--fieldmap_dir", type=Path, help="Fieldmap directory")
    parser.add_argument("--workdir", type=Path, help="Workflow directory")
    parser.add_argument("--fmap_mode", help="Fieldmap type",default="phasediff")
    return parser

def sdcflows_pepolar_fieldmap(fmap_sources, subject, session,fieldmap_dir,workdir):
    estimator = sfm.FieldmapEstimation (
        sources = fmap_sources
    )

    pepolar_wf = estimator.get_workflow()

    fm_wf = Workflow(name = "sdcflows_pepolar_wf", base_dir=workdir)
    sinker = Node(DataSink(),name='fmap_sink')
    sinker.inputs.base_directory = os.path.dirname(fieldmap_dir)
    sinker.inputs.substitutions = [
        ('reoriented',f"sub-{subject}_ses-{session}_desc-preproc_fieldmap"),
        ('dir-AP_epi_average_merged_padded_sliced_volreg_base_fieldcoef_fixed',f"desc-coeff_fieldmap"),
        ('dir-PA_epi_average_merged_padded_sliced_volreg_base_fieldcoef_fixed',f"desc-coeff_fieldmap"),
        ('clipped',f"sub-{subject}_ses-{session}_desc-magnitude_fieldmap")
    ]
    basename = os.path.basename(fieldmap_dir)
    fm_wf.connect( pepolar_wf,"outputnode.fmap",sinker,f"{basename}")
    fm_wf.connect( pepolar_wf,"outputnode.fmap_coeff",sinker,f"{basename}.@coeff")
    fm_wf.connect( pepolar_wf,"outputnode.fmap_mask",sinker,f"{basename}.@mask")
    fm_wf.connect( pepolar_wf,"outputnode.fmap_ref",sinker,f"{basename}.@ref")

    fm_wf.run()

def sdcflows_phdiff_fieldmap(fmap_sources, subject, session,fieldmap_dir,workdir):
    estimator = sfm.FieldmapEstimation (
        sources = fmap_sources
    )

    phdiff_wf = estimator.get_workflow()

    fm_wf = Workflow(name = "sdcflows_phdiff_wf", base_dir=workdir)
    sinker = Node(DataSink(),name='fmap_sink')
    sinker.inputs.base_directory = os.path.dirname(fieldmap_dir)
    sinker.inputs.substitutions = [
        ('clipped',f"sub-{subject}_ses-{session}_desc-magnitude_fieldmap"),
        ('phase1_rads_phdiff_unwrapped_fmap_extra',f"desc-preproc_fieldmap")
    ]
    basename = os.path.basename(fieldmap_dir)
    fm_wf.connect(phdiff_wf,"outputnode.fmap",sinker,f"{basename}")
    fm_wf.connect(phdiff_wf,"outputnode.fmap_coeff",sinker,f"{basename}.@coeff")
    fm_wf.connect(phdiff_wf,"outputnode.fmap_mask",sinker,f"{basename}.@mask")
    fm_wf.connect(phdiff_wf,"outputnode.fmap_ref",sinker,f"{basename}.@ref")

    fm_wf.run()

def main():
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()
    fmap_sources = args.fmap_sources
    subject = args.subject
    session = args.session
    fieldmap_dir = str(args.fieldmap_dir)
    workdir = str(args.workdir)
    fmap_mode = args.fmap_mode

    if fmap_mode == "phasediff":
        sdcflows_phdiff_fieldmap(fmap_sources, subject, session,fieldmap_dir,workdir)
    elif fmap_mode == "pepolar":
        sdcflows_pepolar_fieldmap(fmap_sources, subject, session,fieldmap_dir,workdir)
        

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()


