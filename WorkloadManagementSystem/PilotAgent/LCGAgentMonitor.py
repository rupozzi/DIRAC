########################################################################
# $Id: LCGAgentMonitor.py,v 1.1 2008/01/11 18:17:53 paterson Exp $
# File :   LCGAgentMonitor.py
# Author : Stuart Paterson
########################################################################

""" The LCG Agent Monitor performs the pilot job status tracking activity for LCG.
"""

__RCSID__ = "$Id: LCGAgentMonitor.py,v 1.1 2008/01/11 18:17:53 paterson Exp $"

from DIRACEnvironment                                        import DIRAC
from DIRAC.Core.Utilities.Subprocess                         import shellCall
from DIRAC.ConfigurationSystem.Client.LocalConfiguration     import LocalConfiguration
from DIRAC.WorkloadManagementSystem.PilotAgent.AgentMonitor  import AgentMonitor
from DIRAC                                                   import S_OK, S_ERROR, gConfig, gLogger

import os, sys, re, string, time

class LCGAgentMonitor(AgentMonitor):

  #############################################################################
  def __init__(self):
    """ Standard constructor
    """
    self.log = gLogger
    self.log.setLevel('debug')
    self.cmd = 'edg-job-status'
    self.cmdTimeout = 60

  #############################################################################
  def getPilotStatus(self,jobID,pilotID):
    """Get LCG job status information using the job's owner proxy and
       LCG job IDs. Returns for each JobID its status in the LCG WMS and
       its destination CE as a tuple of 2 elements
    """
    self.log.verbose( '--- Executing %s for %s' %(cmd,jobID) )
    self.__checkProxy()

    cmd = "%s %s" % (self.cmd,pilotID)
    result = self.__exeCommand(cmd)

    if not result['OK']:
      self.log.warn(result)
      return result

    status = result['Status']
    stdout = result['StdOut']
    queryTime = result['Time']

    self.log.verbose( '>>> LCG status query time %.2fs' % queryTime )
    if status == 0:
      lines = output.split('\n')
      for line in lines:
        if line.find('Current Status:') != -1 :
          jobstatus = re.search(':\s+(\w+)',line).group(1)
        if line.find('Destination:') != -1 :
          destination = line.split()[1].split(":")[0]

      self.log.debug('JobID: %s, PilotStatus: %s, Destination: %s' %(jobID,status,destination))
      pilot = S_OK()
      pilot['JobID']=jobID
      pilot['PilotStatus']=status
      pilot['Destination']=destination
      if status == 'Aborted':
        pilot['Aborted']=True
      elif status == 'Waiting' or status == 'Ready' or status == 'Scheduled' or status == 'Submitted':
        pilot['Aborted']=False

      return pilot
    else:
      return result

  #############################################################################
  def __checkProxy(self):
    """Print some debugging information for the current proxy.
    """
    proxyInfo = shellCall(self.cmdTimeout,'grid-proxy-info -debug')
    status = proxyInfo['Value'][0]
    stdout = proxyInfo['Value'][1]
    stderr = proxyInfo['Value'][2]
    self.log.debug('Status %s' %status)
    self.log.debug(stdout)
    self.log.debug(stderr)

  #############################################################################
  def __exeCommand(self,cmd):
    """Runs a submit / list-match command and prints debugging information.
    """
    start = time.time()
    self.log.debug( cmd )
    result = shellCall(60,cmd)

    status = result['Value'][0]
    stdout = result['Value'][1]
    stderr = result['Value'][2]
    self.log.debug('Status = %s' %status)
    self.log.debug(stdout)
    if stderr:
      self.log.warn(stderr)
    result['Status']=status
    result['StdOut']=stdout
    result['StdErr']=stderr
    subtime = time.time() - start
    result['Time']=subtime
    return result

###############################################################################
if __name__ == "__main__":
  """ Main execution method.
  """
  localCfg = LocalConfiguration()
  localCfg.setConfigurationForScript('LCGAgentMonitor')
  localCfg.addMandatoryEntry( "/DIRAC/Setup" )
  localCfg.addDefaultEntry( "/DIRAC/Security/UseServerCertificate", "yes" )
  resultDict = localCfg.loadUserData()

  pollingTime = 100

  if not resultDict[ 'OK' ]:
    gLogger.warn( "There were errors when loading configuration", resultDict[ 'Message' ] )
    sys.exit(1)

  monitor = AgentMonitor('LCG')
  monitor.run()

  #EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#
