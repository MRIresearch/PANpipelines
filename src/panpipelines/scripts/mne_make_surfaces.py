from nipype import logging as nlogging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from functools import partial
import os
import mne

IFLOGGER=nlogging.getLogger('nipype.interface')

def parse_params():
    parser = ArgumentParser(description="MNE make surface")
    parser.add_argument("--subject", help="Subject")
    parser.add_argument("--subjects_dir", type=Path, help="Freesurfer subjects directory")
    return parser

def make_surfaces(subject, subjects_dir):
    mne.bem.make_scalp_surfaces(subject, subjects_dir, force=True, overwrite=True, no_decimate=False, verbose=None)
    mne.bem.make_watershed_bem(subject, subjects_dir, overwrite=True, show=False)

def main():
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()
    subject = args.subject
    subjects_dir = str(args.subjects_dir)

    make_surfaces(subject,subjects_dir)

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()


