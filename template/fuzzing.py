#!/usr/bin/python

import sys
import os.path
import os

# import parent dir as pytohn search path
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

import framework

PROJDIR = os.getcwd() + "/"
BASEDIR = os.path.realpath(PROJDIR + "/../")


config = {
    # name of the software we fuzz
    "name": "",

    # which version of the software are we fuzzing (optional)
    "version": "",

    # additional comment about this project (optional)
    "comment": "",

    # Path to target
    "target_bin": PROJDIR + "bin/server",

    # target arguments
    # separate arguments by space
    # keywords: ""%(port)i" is the port the server will be started on
    "target_args": "%(port)i",

    # if you cant specify the port on the command line,
    # hardcode it here. Note that it will work only with one fuzzing instance.
    "baseport": 20000,

    # how many fuzzing instances should we start
    "processes": 1,

    # "tcp" or "udp" protocol?
    "ipproto": "tcp",

    # STOP.
    # no need to change after this line, usually

    # hongg stuff
    "honggpath": "/opt/honggfuzz/honggfuzz",
    "honggcov": None,
    "honggmode_option": None,  # will be overwritten based on honggcov

    # should we abort if aslr is enabled?
    "ignore_aslr_status": True,

    # have a special app protocol implemented? use it here
    "proto": None,

    # the maximum network message number we will look at
    # (send, replay, test etc.)
    "maxmsg": None,

    # the maximum network message number we will fuzz
    "maxfuzzmsg": None,

    # analyze the response of the server?
    "response_analysis": True,

    # input/output for fuzzer is generated here (so he can mutate it)
    # also ASAN log files
    "temp_dir": PROJDIR + "temp",

    # keep generated output files
    "keep_temp": False,

    # fuzzing results are stored in out/
    "outcome_dir": PROJDIR + "out",

    # which fuzzer should be used
    # currently basically only radamsa
    "fuzzer": "Radamsa",

    #Dharma grammars
    "grammars": PROJDIR + "grammars/",

    # Directory of input files
    "inputs": PROJDIR + "in",

    # Directory of verified files
    "verified_dir": PROJDIR + "verified",

    # dont change this
    "basedir": BASEDIR,
    "projdir": PROJDIR,

    # restart server every X fuzzing iterations
    "restart_server_every": 10000,
}


def main():
    framework.realMain(config)


if __name__ == '__main__':
    sys.exit(main())
