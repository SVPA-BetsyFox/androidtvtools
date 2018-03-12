# androidtvtools
Here you'll eventually find more, but for now, contents as follows:

* auditapps
  A NodeJS (requires >v6.9.0) script to iterate over all ADB connected devices, and produce a report of all installed apps, along with their corresponding versions, APK paths, package names.

  Installation:
    * Make sure you're running at least NodeJS v6.9.0
    * Clone this repo
    * From a command line, in the folder you cloned the repo to, run `npm install`
    * Using ADB, connect to the device(s) you wish to audit
    * Run `./auditapps`
----

* keepalive.sh
  A shell script that will attempt to maintain a connection to a device over ADB. When called with a list of IP addresses as parameters, will attempt to reconnect to any devices that no longer appear as connected. Performs check once every 1.5 seconds.