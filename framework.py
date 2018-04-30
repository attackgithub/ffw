#!/usr/bin/env python

# FFW - Fuzzing For Worms
# Author: Dobin Rutishauser

import logging
import argparse
import os
import glob

from network import replay
from network.interceptor import Interceptor
from clientfuzzer import clientfuzzermaster
from verifier import verifier
from verifier import minimizer
from uploader import uploader
from network import tester
from network import proto_vnc

from basicmode import basicmaster
from honggmode import honggmaster
from configmanager import ConfigManager


# https://stackoverflow.com/questions/9321741/printing-to-screen-and-writing-to-a-file-at-the-same-time
def setupLoggingWithFile(config):
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename='ffw-debug.log',
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.WARN)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    # slaves will setup their own logging
    config["DebugWithFile"] = True


def setupLoggingStandard():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M')


def realMain(config):
    parser = argparse.ArgumentParser("Fuzzing For Worms")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--intercept', help='Intercept and record network communication', action="store_true")
    group.add_argument('--test', help='Test intercepted network communication', action="store_true")
    group.add_argument('--fuzz', help='Perform fuzzing', action="store_true")
    group.add_argument('--clientfuzz', help='Perform client fuzzing', action="store_true")
    group.add_argument('--honggmode', help='Perform honggfuze based fuzzing', action="store_true")
    group.add_argument('--verify', help='Verify crashes', action="store_true")
    group.add_argument('--minimize', help='Minimize crashes', action="store_true")
    group.add_argument('--replay', help='Replay a crash', action="store_true")
    group.add_argument('--upload', help='Upload verified crashes', action="store_true")

    parser.add_argument('--debug', help="More error messages, only one process", action="store_true")
    parser.add_argument('--gui', help='Fuzzer: Use ncurses gui', action="store_true")
    parser.add_argument('--processes', help='Fuzzer: How many paralell processes', type=int)

    # TODO: make this mode specific
    parser.add_argument("--honggcov", help="Select Honggfuzz coverage: hw/sw", default="sw")
    parser.add_argument('--listenport', help='Intercept: Listener port', type=int)
    parser.add_argument('--targetport', help='Intercept/Replay: Port to be used for the target server', type=int)
    parser.add_argument('--file', help="Verify/Replay: Specify file to be used")
    parser.add_argument('--url', help="Uploader: url")
    parser.add_argument('--basic_auth_user', help='Uploader: basic auth user')
    parser.add_argument('--basic_auth_password', help='Uploader: basic auth password')
    parser.add_argument('--adddebuglogfile', help='Will write a debug log file', action="store_true")

    parser.add_argument('--config', help='Config file')
    parser.add_argument('--basedir', help='FFW base directory')
    args = parser.parse_args()

    # wtf is this
    configManager = ConfigManager()
    if config is None:
        if args.config is None:
            print "No config specified. Either start via fuzzing.py, or with --config <configfile>"
            return False
        else:
            if not args.basedir:
                print "Please specify FFW basedir"
                return False
            else:
                config = configManager.loadConfigByFile(args.config, args.basedir)
                if config is None:
                    print "Invalid config"
                    return False

    if not configManager.checkRequirements(config):
        print "Requirements not met."
        return

    # TODO remove this from here
    if config["proto"] == "vnc":
        print("Using protocol: vnc")
        config["protoObj"] = proto_vnc.ProtoVnc()
    else:
        config["protoObj"] = None

    if args.processes:
        config["processes"] = args.processes

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        config["processes"] = 1
        config["debug"] = True
    else:
        config["debug"] = False

    if args.adddebuglogfile:
        setupLoggingWithFile(config)
    else:
        setupLoggingStandard()

    if args.intercept:
        ffwIntercept(config, args)

    if args.test:
        ffwTest(config, args)

    if args.fuzz:
        ffwBasicFuzz(config, args)

    if args.clientfuzz:
        ffwClientFuzz(config, args)

    if args.honggmode:
        ffwHonggmode(config, args)

    if args.verify:
        ffwVerify(config, args)

    if args.minimize:
        ffwMinimize(config, args)

    if args.replay:
        ffwReplay(config, args)

    if args.upload:
        ffwUpload(config, args)


def ffwIntercept(config, args):
    interceptorPort = 10000
    targetPort = 20000

    if args.listenport:
        interceptorPort = args.listenport

    if args.targetport:
        targetPort = args.targetport
    else:
        targetPort = config["target_port"]

    print("Interceptor listen on port: " + str(interceptorPort))
    print("Target server port: " + str(targetPort))

    interceptor = Interceptor(config)
    interceptor.doIntercept(interceptorPort, targetPort)


def ffwTest(config, args):
    t = tester.Tester(config)
    t.test()


def ffwBasicFuzz(config, args):
    if not configManager.checkFuzzRequirements(config):
        return False
    basicmaster.doFuzz(config, args.gui)


def ffwHonggmode(config, args):
    if not configManager.checkFuzzRequirements(config):
        return False

    if args.honggcov == "hw" or config["honggcov"] == "hw":
        config["honggmode_option"] = "--linux_perf_bts_edge"

        if os.geteuid() != 0:
            logging.error('"--honggcov hw" hardware coverage requires root')
            return

    elif args.honggcov == "sw" or config["honggcov"] == "sw":
        config["honggmode_option"] = None  # sw is default
    else:
        config["honggmode_option"] = None

    honggmaster.doFuzz(config)


def ffwClientFuzz(config, args):
    if not configManager.checkFuzzRequirements(config):
        return False
    clientfuzzermaster.doFuzz(config, args.gui)


def ffwVerify(config, args):
    v = verifier.Verifier(config)

    if args.file:
        v.verifyFile(args.file)
    else:
        v.verifyOutDir()


def ffwMinimize(config, args):
    mini = minimizer.Minimizer(config)
    mini.minimizeOutDir()


def ffwReplay(config, args):
    replayer = replay.Replayer(config)

    if not args.file:
        print "Use --file to specify a file to be replayed"
    elif not args.targetport:
        print "Use --targetport to specify port to send data to"
    else:
        replayer.replayFile(args.targetport, args.file)


def ffwReplay(config, args):
    if args.basic_auth_user and args.basic_auth_password:
        u = uploader.Uploader(config, args.url, args.basic_auth_user, args.basic_auth_password)
    else:
        u = uploader.Uploader(config, args.url, None, None)

    u.uploadVerifyDir()
