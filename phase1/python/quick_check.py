#!/usr/bin/env python3
import glob, os, json
logdir = r"D:\alphalyceum\phase1\logs"
outs = sorted(glob.glob(os.path.join(logdir, "watcher_*.out.log")), key=os.path.getmtime, reverse=True)
errs = sorted(glob.glob(os.path.join(logdir, "watcher_*.err.log")), key=os.path.getmtime, reverse=True)
if outs:
    print("=== Latest OUT log (tail 20) ===")
    with open(outs[0], 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(''.join(lines[-20:]))
else:
    print("No watcher out logs found")
if errs:
    print("\n=== Latest ERR log (tail 20) ===")
    with open(errs[0], 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(''.join(lines[-20:]))
else:
    print("No watcher err logs found")
