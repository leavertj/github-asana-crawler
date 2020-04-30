from github import Github
import re


# g = Github(GITHUB_TOKEN)

# user = g.get_user()

# for org in user.get_orgs():
#     print(org.id)
#     print(org.login)

def parse_asana_ticket_name(ticket_name):
    pattern = "([a-zA-z0-9-_]+)\-\[([0-9]+)\-([0-9NEW]+)\]- (.+)"
    matches = re.search(pattern, ticket_name)
    if matches:
        return [matches.group(1),matches.group(2),matches.group(3),matches.group(4)]
    else: 
        return None

parse_asana_ticket_name("aws-control-tower-customizations-[604737851-NEW]- Log messages don't detail which stack/account/region caused the error")