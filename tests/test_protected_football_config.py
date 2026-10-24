import copy
import unittest
from scripts.protected_football_config import validate_football_config

class FootballConfigTests(unittest.TestCase):
    def setUp(self):
        self.protected={'schema_version':1,'path_candidates':{'roster':['/roster']},'age_discovery':{'enabled':True},
            'teams':[{'team':'Synthetic','division':'FBS','candidate_roots':['https://official.example'],
            'known_u18':[],'mapped':False,'schedule_url':'https://official.example/schedule','official_root':'https://official.example'}]}
    def test_generated_fields_and_official_host_path_updates_allowed(self):
        value=copy.deepcopy(self.protected);value['last_auto_map_run']='2026-10-24T00:00:00Z'
        value['teams'][0].update(mapped=True,mapping_status='AUTO-MAPPED',roster_url='https://official.example/football/roster')
        validate_football_config(self.protected,value)
    def test_private_output_cannot_change_team_config_or_host(self):
        mutations=[lambda d:d['path_candidates'].update(roster=['/changed']),
            lambda d:d['teams'][0].update(team='Another'),lambda d:d['teams'][0].update(division='Other'),
            lambda d:d['teams'][0].update(candidate_roots=['https://attacker.example']),
            lambda d:d['teams'][0].update(roster_url='https://attacker.example/roster'),
            lambda d:d['teams'][0].update(roster_url='javascript:alert(1)'),
            lambda d:d['teams'][0].update(mapped=1),lambda d:d['teams'].append(copy.deepcopy(d['teams'][0]))]
        for mutate in mutations:
            value=copy.deepcopy(self.protected);mutate(value)
            with self.assertRaises(ValueError):validate_football_config(self.protected,value)

if __name__=='__main__':unittest.main()
