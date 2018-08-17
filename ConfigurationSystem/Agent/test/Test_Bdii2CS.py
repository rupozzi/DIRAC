#!/bin/env python
"""
Tests for Bdii2CSAgent module
"""

import logging
import unittest
import pytest

from mock import MagicMock as Mock, patch

from DIRAC import S_OK, S_ERROR
from DIRAC.ConfigurationSystem.Agent import Bdii2CSAgent

from DIRAC.tests.Utilities.assertingUtils import checkAgentOptions

MODNAME= "DIRAC.ConfigurationSystem.Agent.Bdii2CSAgent"

MAINBDII = { 'site1': {'CEs': { 'ce1': { 'Queues': { 'queue1': "SomeValues" }}}},
             'site2': {'CEs': { 'ce2': { 'Queues': { 'queue2': "SomeValues" }}}}
           }
ALTBDII = { 'site2': {'CEs': { 'ce2': { 'Queues': { 'queue2': "SomeOtherValues" }},
                               'ce2b': { 'Queues': { 'queue2b': "SomeOtherValues" }}}},
            'site3': {'CEs': { 'ce3': { 'Queues': { 'queue3': "SomeValues" }}}}
          }


@pytest.fixture
def bdii2CSAgent():
  """Return an instance of the TransformationCleaningAgent."""
  with patch(MODNAME + ".AgentModule.__init__", new=Mock()):
    agent = Bdii2CSAgent.Bdii2CSAgent(agentName="sys/name", loadName="sys/name")
    # as we ignore the init from the baseclass some agent variables might not be present so we set them here
    # in any case with this we can check that log is called with proper error messages
    agent.log = Mock()
  return agent


def test_AgentOptions(caplog, bdii2CSAgent):
  """Check that all options in ConfigTemplate are found in the initialize method, including default values."""
  caplog.set_level(logging.DEBUG)
  bdii2CSAgent.am_getOption = Mock()
  with patch("DIRAC.ConfigurationSystem.Agent.Bdii2CSAgent.getVOs", new=Mock(return_value=S_ERROR())), \
          patch("DIRAC.ConfigurationSystem.Agent.Bdii2CSAgent.CSAPI", new=Mock()):
    bdii2CSAgent.initialize()
  checkAgentOptions(bdii2CSAgent.am_getOption, 'ConfigurationSystem', 'Bdii2CSAgent',
                    ignoreOptions=['BannedCEs', 'BannedSEs', 'DryRun'])


class Bdii2CSTests( unittest.TestCase ):

  def setUp( self ):
    with patch( "DIRAC.ConfigurationSystem.Agent.Bdii2CSAgent.AgentModule.__init__", new=Mock() ):
      self.agent = Bdii2CSAgent.Bdii2CSAgent( agentName="Configuration/testing", loadName="Configuration/testing" )

      ## as we ignore the init from the baseclass some agent variables might not be present so we set them here
      ## in any case with this we can check that log is called with proper error messages
      self.agent.log = Mock()


  def tearDown( self ):
    pass


  def test__getBdiiCEInfo_success( self ):

    expectedResult = {}
    expectedResult.update( ALTBDII )
    expectedResult.update( MAINBDII )

    self.agent.alternativeBDIIs = [ "server2" ]
    with patch( MODNAME+".getBdiiCEInfo",
                new=Mock( side_effect=[
                  S_OK( MAINBDII ),
                  S_OK( ALTBDII ),
                ] )
              ) as infoMock:
      ret = self.agent._Bdii2CSAgent__getBdiiCEInfo( "vo" ) #pylint: disable=no-member
      infoMock.assert_any_call("vo", host=self.agent.host, glue2=self.agent.glue2Only)
      infoMock.assert_any_call("vo", host="server2", glue2=self.agent.glue2Only)
    self.assertTrue( ret['OK'] )
    self.assertEqual( expectedResult, ret['Value'] )
    self.assertEqual( ret['Value']['site2']['CEs']['ce2']['Queues']['queue2'], "SomeValues" )
    self.assertNotIn( 'ce2b', ret['Value']['site2']['CEs'] )


  def test__getBdiiCEInfo_fail_10( self ):

    self.agent.alternativeBDIIs = [ "server2" ]
    with patch( MODNAME+".getBdiiCEInfo",
                new=Mock( side_effect=[
                  S_ERROR( "error" ),
                  S_OK( ALTBDII ),
                ] )
              ) as infoMock:
      ret = self.agent._Bdii2CSAgent__getBdiiCEInfo( "vo" ) #pylint: disable=no-member
      infoMock.assert_any_call("vo", host=self.agent.host, glue2=self.agent.glue2Only)
      infoMock.assert_any_call("vo", host="server2", glue2=self.agent.glue2Only)
      self.assertTrue( any ( "Failed getting information from default" in str(args) \
                             for args in self.agent.log.error.call_args_list ),
                       self.agent.log.error.call_args_list )
    self.assertTrue( ret['OK'] )
    self.assertEqual( ALTBDII, ret['Value'] )

  def test__getBdiiCEInfo_fail_01( self ):


    self.agent.alternativeBDIIs = [ "server2" ]
    with patch( MODNAME+".getBdiiCEInfo",
                new=Mock( side_effect=[
                  S_OK( MAINBDII ),
                  S_ERROR( "error" ),
                ] )
              ) as infoMock:
      ret = self.agent._Bdii2CSAgent__getBdiiCEInfo( "vo" ) #pylint: disable=no-member
      infoMock.assert_any_call("vo", host="server2", glue2=False)
      infoMock.assert_any_call("vo", host="server2", glue2=False)
      self.assertTrue( any ( "Failed getting information from server2" in str(args) \
                             for args in self.agent.log.error.call_args_list ),
                       self.agent.log.error.call_args_list )
    self.assertTrue( ret['OK'] )
    self.assertEqual( MAINBDII, ret['Value'] )


  def test__getBdiiCEInfo_fail_11( self ):

    self.agent.alternativeBDIIs = [ "server2" ]
    with patch( MODNAME+".getBdiiCEInfo",
                new=Mock( side_effect=[
                  S_ERROR( "error1" ),
                  S_ERROR( "error2" ),
                ] )
              ) as infoMock:
      ret = self.agent._Bdii2CSAgent__getBdiiCEInfo( "vo" ) #pylint: disable=no-member
      infoMock.assert_any_call("vo", host=self.agent.host, glue2=False)
      infoMock.assert_any_call("vo", host="server2", glue2=False)
      self.assertTrue( any ( "Failed getting information from server2" in str(args) \
                             for args in self.agent.log.error.call_args_list ),
                       self.agent.log.error.call_args_list )
      self.assertTrue( any ( "Failed getting information from default" in str(args) \
                             for args in self.agent.log.error.call_args_list ),
                       self.agent.log.error.call_args_list )

    self.assertFalse( ret['OK'] )
    self.assertIn( "error1\nerror2", ret['Message'] )


if __name__ == '__main__':
  SUITE = unittest.defaultTestLoader.loadTestsFromTestCase( Bdii2CSTests )
  unittest.TextTestRunner( verbosity = 2 ).run( SUITE )
