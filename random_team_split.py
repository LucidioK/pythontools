#!/usr/bin/env python
import json
import random
import re
import sys

args = sys.argv[1:]
if len(args) == 0 or any(re.match('^(-h|--help|-\?|--\?)$', arg) for arg in args):
    print('random_team_split.py people teams')
    print('Example:')
    print(" random_team_split.py 'Brandon,Connor,Di,Raul,Robert,Yale' 'Blue,Yellow'")
    exit(1)    

people      = sorted(set(args[0].split(',')))
team_seeds  = sorted(set(args[1].split(',')))
team_count  = len(team_seeds)
teams       = []
for i in range(len(people)):
    teams.append(team_seeds[i%team_count])

person_team = dict([(person,'') for person in people])
team_person = dict([(team,[]) for team in team_seeds])

for person in people:
    selected_team = random.choice(teams)
    person_team[person] = selected_team
    team_person[selected_team].append(person)
    teams.remove(selected_team)

print('\n\nPerson --> Team:')
print(json.dumps(person_team, indent=2))
print('\n\nTeam --> Person:')
print(json.dumps(team_person, indent=2))
