"""SPDX-License-Identifier: AGPL-3.0-or-later"""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv)>1 and sys.argv[1]=='--yoondf-font-job':
        from bichaek.font_jobs import main
        main(sys.argv[2:]);sys.exit(0)
    from bichaek.app import run
    sys.exit(run())
