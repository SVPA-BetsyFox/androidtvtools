import os, subprocess, re, time, codecs, sys, json, hashlib, inspect, random, functools
import urllib.request
import ssl
from appJar import gui

jobs = []
job_id = 0
total_jobs = 0
unfinished_jobs = 0


def add_log(log):
  ui.openScrollPane("app_report")
  ui.addLabel(f'lbl{log}')
  ui.stopScrollPane()


def add_job(func = lambda x: longtask(x), params={}):
  global jobs, job_id, total_jobs, unfinished_jobs
  job_id += 1
  total_jobs += 1
  unfinished_jobs += 1
  jobs.append({ "call":func, "params": params, "id": job_id })


def longtask(returnval):
  print("long task beginning...")
  time.sleep(random.randint(2, 10))
  return "WHAT WHAT"

def complete_job(id):
  global unfinished_jobs
  print(f'finished job #{id}')
  unfinished_jobs -= 1
  update_progress()



def threadulate(func):
  global ui
  print(f'added job #{func["id"]}')
  ui.threadCallback(lambda: func["call"](func["params"]), lambda x: complete_job(func["id"]))


def update_progress():
  global ui, unfinished_jobs, total_jobs
  percent = (1 - (unfinished_jobs / total_jobs)) * 100
  # print(percent)
  ui.setMeter("progress", percent)


def start():
  global jobs
  while jobs:
    job = jobs.pop()
  # for job in jobs:
    add_log(f'threadulated {job["id"]}')
    threadulate(job)


ui = gui("Betsy's Sandbox, Yes!", "1280x1024")
ui.addButton("Yoink!", start)

ui.startScrollPane("app_report", row=1, colspan=2, rowspan=2)

ui.setBg("#beeeef")
ui.addLabel(f'Log!')


ui.stopScrollPane()

ui.setSticky("sew")
ui.addMeter("progress", row=2, colspan=2)
ui.setMeterFill("progress", "blue")
ui.setMeterBg("progress", "black")
ui.setMeterFg("progress", "gold")



for i in range(0,1000):
  msg = f'THIS IS THE RESULT OF JOB #{i}'
  add_job(lambda i: longtask(i), msg)


ui.go()