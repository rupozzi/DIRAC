""" Collection of utilities for finding paths in the CS
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__RCSID__ = "$Id$"

from six.moves.urllib import parse as urlparse

from DIRAC.Core.Utilities import List
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData


def getDIRACSetup():
  """ Get DIRAC default setup name

      :return: str
  """
  return gConfigurationData.extractOptionFromCFG("/DIRAC/Setup")


def divideFullName(entityName, componentName=None):
  """ Convert component full name to tuple

      :param str entityName: component full name, e.g.: 'Framework/ProxyManager'
      :param str componentName: component name

      :return: tuple -- contain system and component name
  """
  entityName = strip('/')
  if entityName and '/' not in entityName and componentName:
    return (entityName, componentName)
  fields = [field.strip() for field in entityName.split("/") if field.strip()]
  if len(fields) == 2:
    return tuple(fields)
  raise RuntimeError("Service (%s) name must be with the form system/service" % entityName)


def getSystemInstance(system, setup=False):
  """ Find system instance name

      :param str system: system name
      :param str setup: setup name

      :return: str
  """
  optionPath = "/DIRAC/Setups/%s/%s" % (setup or getDIRACSetup(), system)
  instance = gConfigurationData.extractOptionFromCFG(optionPath)
  if not instance:
    raise RuntimeError("Option %s is not defined" % optionPath)
  return instance


def getSystemSection(system, instance=False, setup=False):
  """ Get system section

      :param str system: system name
      :param str instance: instance name
      :param str setup: setup name

      :return: str -- system section path
  """
  system, _ = divideFullName(system, '_')  # for backward compatibility
  return "/Systems/%s/%s" % (system, instance or getSystemInstance(system, setup=setup))


def getComponentSection(system, component=False, setup=False, componentCategory="Services"):
  """Function returns the path to the component.

  :param str system: system name or component name prefixed by the system in which it is placed.
                     e.g. 'WorkloadManagement/SandboxStoreHandler'
  :param str component: component name, e.g. 'SandboxStoreHandler'
  :param str setup: Name of the setup.
  :param str componentCategory: Category of the component, it can be:
                                'Agents', 'Services', 'Executors' or 'Databases'.

  :return str: Complete path to the component

  :raise RuntimeException: If in the system - the system part does not correspond to any known system in DIRAC.

  Examples:
    getComponentSection('WorkloadManagement/SandboxStoreHandler', setup='Production', componentCategory='Services')
    getComponentSection('WorkloadManagement', 'SandboxStoreHandler', 'Production')
  """
  system, component = divideFullName(system, component)
  return "%s/%s/%s" % (getSystemSection(system, setup=setup), componentCategory, component)


def getServiceSection(system, serviceName=False, setup=False):
  """ Get service section in a system

      :param str system: system name
      :param str serviceName: DB name

      :return: str
  """
  return getComponentSection(system, component=serviceName, setup=setup)


def getAgentSection(system, agentName=False, setup=False):
  """ Get agent section in a system

      :param str system: system name
      :param str agentName: DB name

      :return: str
  """
  return getComponentSection(system, component=agentName, setup=setup, componentCategory="Agents")


def getExecutorSection(system, executorName=None, component=False, setup=False):
  """ Get executor section in a system

      :param str system: system name
      :param str executorName: DB name

      :return: str
  """
  return getComponentSection(system, component=executorName, setup=setup, componentCategory="Executors")


def getDatabaseSection(system, dbName=False, setup=False):
  """ Get DB section in a system

      :param str system: system name
      :param str dbName: DB name

      :return: str
  """
  return getComponentSection(system, component=dbName, setup=setup, componentCategory="Databases")


def getSystemURLSection(system, setup=False):
  """ Get URLs section in a system

      :param str system: system name
      :param str setup: setup name

      :return: str
  """
  return "%s/URLs" % getSystemSection(system, setup=setup)


def checkServiceURL(serviceURL, system=None, service=None):
  """ Check service URL

      :param str serviceURL: full URL, e.g.: dips://some-domain:3424/Framework/Service
      :param str system: system name
      :param str service: service name

      :return: str
  """
  url = urlparse.urlparse(serviceURL)
  # Check port
  if not url.port:
    if url.scheme == 'dips':
      raise RuntimeError('No port found for %s/%s URL!' % (system, service))
    url = url._replace(netloc=url.netloc + ':' + str(80 if url.scheme == 'http' else 443))
  # Check path
  if not url.path.strip('/'):
    if not system or not service:
      raise RuntimeError('No path found for %s/%s URL!' % (system, service))
    url = url._replace(path='/%s/%s' % (system, service))
  return url.geturl()


def getSystemURLs(system, setup=False, failover=False):
  """
    Generate url.

    :param str system: system name or full name e.g.: Framework/ProxyManager
    :param str setup: DIRAC setup name, can be defined in dirac.cfg
    :param bool failover: to add failover URLs to end of result list

    :return: dict -- complete urls. e.g. [dips://some-domain:3424/Framework/Service]
  """
  urlDict = {}
  for service in gConfigurationData.getOptionsFromCFG("%s/URLs" % getSystemSection(system, setup=setup)):
    urlDict[service] = getServiceURLs(system, service, setup=setup, failover=failover)
  return urlDict


def getServiceURLs(system, service=None, setup=False, failover=False):
  """
    Generate url.

    :param str system: system name or full name e.g.: Framework/ProxyManager
    :param str service: service name, like 'ProxyManager'.
    :param str setup: DIRAC setup name, can be defined in dirac.cfg
    :param bool failover: to add failover URLs to end of result list

    :return: list -- complete urls. e.g. [dips://some-domain:3424/Framework/Service]
  """
  system, service = divideFullName(system, service)
  resList = []
  mainServers = None
  systemSection = getSystemSection(system, setup=setup)

  # Add failover URLs at the end of the list
  failover = "Failover" if failover else ""
  for fURLs in ["", "Failover"] if failover else [""]:
    urlList = []
    urls = List.fromChar(gConfigurationData.extractOptionFromCFG("%s/%sURLs/%s" % (systemSection, fURLs, service)))

    # Be sure that urls not None
    for url in urls or []:

      # Trying if we are refering to the list of main servers
      # which would be like dips://$MAINSERVERS$:1234/System/Component
      if '$MAINSERVERS$' in url:
        if not mainServers:
          # Operations cannot be imported at the beginning because of a bootstrap problem
          from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
          mainServers = Operations(setup=setup).getValue('MainServers', [])
        if not mainServers:
          raise Exception("No Main servers defined")

        for srv in mainServers:
          _url = checkServiceURL(url.replace('$MAINSERVERS$', srv), system, service)
          if _url not in urlList:
            urlList.append(_url)
        continue

      _url = checkServiceURL(url, system, service)
      if _url not in urlList:
        urlList.append(_url)

    # Randomize list if needed
    resList.extend(List.randomize(urlList))

  return resList


def getServiceURL(system, setup=False, service=None):
  """
    Generate url.

    :param str system: system name or full name e.g.: Framework/ProxyManager
    :param str setup: DIRAC setup name, can be defined in dirac.cfg
    :param str service: service name, like 'ProxyManager'.

    :return: str -- complete list of urls. e.g. dips://some-domain:3424/Framework/Service, dips://..
  """
  system, service = serviceTuple if serviceTuple else divideFullName(system, service)
  urls = getServiceURLs(system, service=service, setup=setup)
  return ','.join(urls) if urls else ""


def getServiceFailoverURL(system, setup=False, service=None):
  """ Get failover URLs for service

      :param str system: system name or full name, like 'Framework/Service'.
      :param str serviceTuple: unuse!
      :param str setup: DIRAC setup name, can be defined in dirac.cfg
      :param str service: service name, like 'ProxyManager'.

      :return: str -- complete list of urls
  """
  system, service = serviceTuple if serviceTuple else divideFullName(system, service)
  systemSection = getSystemSection(system, setup=setup)
  url = gConfigurationData.extractOptionFromCFG("%s/FailoverURLs/%s" % (systemSection, service))
  return checkServiceURL(url, system, service) if url else ""


def getGatewayURLs(system="", service=None):
  """ Get gateway URLs for service

      :param str system: system name or full name, like 'Framework/Service'.
      :param str service: service name, like 'ProxyManager'.

      :return: list or False
  """
  system, service = divideFullName(system, service)
  siteName = gConfigurationData.extractOptionFromCFG("/LocalSite/Site")
  if not siteName:
    return False
  gateways = gConfigurationData.extractOptionFromCFG("/DIRAC/Gateways/%s" % siteName)
  if not gateways:
    return False
  gateways = List.randomize(List.fromChar(gateways, ","))
  return [checkServiceURL(u, system, service) for u in gateways if u] if system and service else gateways
