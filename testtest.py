import os, subprocess, re, time, codecs, sys, json, hashlib, inspect, random, functools
import urllib.request
import ssl
from appJar import gui

#####################################################################################################

jobs = []
job_id = 0
total_jobs = 0
unfinished_jobs = 0


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


# execute n number of jobs, -1 is default, and any value less than 0 will process *all* jobs in queue, including any added during the process of executing existing jobs
def process_jobs(n=-1):
  global jobs
  while jobs and n != 0:
    if n > 0: n -= 1
    job = jobs.pop()
    debug(f'threadulated {job["id"]}')
    threadulate(job)


for i in range(0,10):
  msg = f'THIS IS THE RESULT OF JOB #{i}'
  add_job(lambda i: longtask(i), msg)


ui.go()