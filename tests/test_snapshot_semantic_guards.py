"""Synthetic held-source/identity transport mutations, not sports-fact testing."""
import copy
from datetime import datetime,timezone
import unittest
from scripts.snapshot_semantic_guards import validate_change
NOW=datetime(2026,10,24,tzinfo=timezone.utc)


class SnapshotSemanticTests(unittest.TestCase):
    def check(self,old,new):validate_change(old,new,now=NOW)
    def reject(self,old,new):
        with self.assertRaises(ValueError):self.check(old,new)

    def test_held_root_preserves_dates_and_observations_not_admin_refresh_time(self):
        old={'collection_paused':True,'stale':True,'access_status':'permission_required',
             'generated_at':'2026-10-01T00:00:00Z','events':[{'id':'held-event','observed_at':None}],
             'collection_hold_recorded_at':'2026-10-22T00:00:00Z'}
        new=copy.deepcopy(old);new['collection_hold_recorded_at']='2026-10-23T00:00:00Z';self.check(old,new)
        for key,value in [('collection_paused',False),('stale',False),('access_status','allowed'),
                          ('generated_at','2026-10-23T00:00:00Z'),('events',[])]:
            new=copy.deepcopy(old);new[key]=value;self.reject(old,new)
        new=copy.deepcopy(old);new['events'][0]['observed_at']='2026-10-23T00:00:00Z';self.reject(old,new)

    def test_all_hold_forms_and_lists_persist(self):
        for field in ('collection_paused','permission_held','permission_required','halted'):
            old={field:True};self.reject(old,{});self.reject(old,{field:False})
        old={'publisher_permission_holds':[{'publisher':'ITF','permission_required':True}]}
        self.reject(old,{'publisher_permission_holds':[]})
        new=copy.deepcopy(old);new['publisher_permission_holds'].append({'publisher':'new','permission_required':True});self.check(old,new)

    def test_nested_held_source_cannot_disappear_reset_or_duplicate(self):
        old={'events':[{'id':'held','collection_paused':True,'generated_at':'2026-10-01T00:00:00Z'}]}
        self.reject(old,{'events':[]})
        new=copy.deepcopy(old);new['events'][0]['collection_paused']=False;self.reject(old,new)
        new=copy.deepcopy(old);new['events'].append(dict(new['events'][0],collection_paused=False));self.reject(old,new)

    def test_schema_two_durable_identity_without_age_evidence_survives(self):
        old={'schema_version':2,'records':[{'official_player_id':'itf:123','name':'Synthetic','age':17,
             'source_url':'https://example.test/player/123','dob':None,'aliases':['Synthetic Name']}]}
        new=copy.deepcopy(old);new['records'][0]['age']=18;new['records'][0]['current_exposure']=False;self.check(old,new)
        self.reject(old,{'schema_version':2,'records':[]})
        for field,value in [('name','Renamed'),('official_player_id','itf:999'),('aliases',[])]:
            new=copy.deepcopy(old);new['records'][0][field]=value;self.reject(old,new)
        new=copy.deepcopy(old);new['records'].append(copy.deepcopy(new['records'][0]));self.reject(old,new)

    def test_reviewed_evidence_exact_types_and_authoritative_fields_preserved(self):
        old={'records':[{'official_player_id':'itf:123','name':'Same','dob':'2009-01-02',
             'last_verified':'2026-10-14','age_evidence':{'review':{'id':'synthetic-reviewed'},'status':'verified_dob','dob':'2009-01-02','count':1}}]}
        for field,value in [('dob','2010-01-02'),('last_verified','2026-10-23'),('official_player_id','itf:other')]:
            new=copy.deepcopy(old);new['records'][0][field]=value;self.reject(old,new)
        new=copy.deepcopy(old);new['records'][0]['age_evidence']['count']=True;self.reject(old,new)
        self.check(old,copy.deepcopy(old))

    def test_unreviewed_durable_identity_can_gain_source_evidence(self):
        old={'schema_version':2,'records':[{'official_player_id':'itf:123','name':'Same','dob':None,'last_verified':'2026-10-01'}]}
        new=copy.deepcopy(old);new['records'][0].update(dob='2009-01-02',last_verified='2026-10-23')
        self.check(old,new)

    def test_reviewed_cache_dictionary_identity_cannot_be_renamed(self):
        old={'records':{'synthetic-key':{'name':'Original','official_player_id':'itf:1','age_evidence':{'review':{'id':'synthetic-reviewed'},'status':'verified_dob','dob':'2009-01-01'}}}}
        new=copy.deepcopy(old);new['records']['synthetic-key']['name']='Renamed';self.reject(old,new)

    def test_preexisting_ambiguous_names_preserved_without_identity_merging(self):
        old={'rows':[{'name':'Same','age_evidence':{'review':{'id':'synthetic-reviewed'},'status':'unknown','source':'one'}},
                     {'name':'Same','age_evidence':{'review':{'id':'synthetic-reviewed'},'status':'unknown','source':'two'}}]}
        self.check(old,copy.deepcopy(old));self.reject(old,{'rows':[old['rows'][0]]})
        new=copy.deepcopy(old);new['another_field']='unrelated';self.check(old,new)

    def test_nonfuture_aware_observation_times_but_future_event_schedule_allowed(self):
        for value in ('2999-01-01T00:00:00Z','2026-10-01T00:00:00','not-a-date','2999-01-01'):
            self.reject({}, {'generated_at':value})
        self.check({}, {'checked_at':'2026-10-14','generated_at':'2026-10-23T00:00:00Z',
                        'start_time':'2027-01-01T00:00:00Z','window_end':'2027-01-01'})

    def test_dangerous_url_schemes_and_controls_rejected(self):
        for key in ('url','source_url','license_url','endpoint','href','source_urls'):
            for value in ('javascript:alert(1)','data:text/html,bad','file:///etc/passwd','https://user:pw@example.test/',
                          'java\nscript:alert(1)',' https://example.test'):
                self.reject({}, {key:value})
        self.check({}, {'source_urls':{'Men':'https://example.test/men','Women':['http://example.test/women']},
                        'source':'Official directory label','url':None})

if __name__=='__main__':unittest.main()
