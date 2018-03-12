# androidtvtools
Here you'll eventually find more, but for now, contents as follows:

* auditapps
  A nodejs script to iterate over all ADB connected devices, and produce a report of all installed apps, along with their corresponding versions, APK paths, package names.

* keepalive.sh
  A shell script that will attempt to maintain a connection to a device over ADB. When called with a list of IP addresses as parameters, will attempt to reconnect to any devices that no longer appear as connected. Performs check once every 1.5 seconds.