from datetime import datetime, timedelta
import json, re

from github import Github
import asana


TEAM_GITHUB_ORG = 'awslabs'
ASANA_PROJECT_GID = '1173676030516145'
ASANA_WORKSPACE_GIT = '1141277692235279'
LOOKBACK=14

REPOS = [
    "awslabs/smart-product-solution",
    "awslabs/iot-device-simulator",
    "awslabs/aws-waf-security-automations",
    "awslabs/serverless-transit-network-orchestrator",
    "awslabs/operations-conductor",
    "awslabs/aws-ops-automator",
    "awslabs/aws-instance-scheduler",
    "awslabs/aws-limit-monitor",
    "awslabs/aws-centralized-logging",
    "awslabs/workspaces-cost-optimizer",
    "awslabs/aws-transit-vpc",
    "awslabs/aws-control-tower-customizations"
]
# REPOS = [
#     #"awslabs/aws-control-tower-customizations",
#     #"awslabs/aws-instance-scheduler",
#     "awslabs/iot-device-simulator",
#     #"awslabs/workspaces-cost-optimizer"
# ]

def get_github_client(access_key):
    return Github(access_key)


def get_asana_client(access_key):
    return asana.Client.access_token(access_key)

'''
Returns the ticket name parsed:
[repo, issueid, last comment id, title]
'''
def parse_asana_ticket_name(ticket_name):
    pattern = "([a-zA-z0-9-_]+)\-\[([0-9]+)\-([0-9NEW]+)\]- (.+)"
    matches = re.search(pattern, ticket_name)
    if matches:
        return matches.group(1),matches.group(2),matches.group(3),matches.group(4)
    else:
        return None

def get_asana_tasks(asana_client, project_gid):
    tasks = {}
    for task in asana_client.tasks.find_by_project(project_gid):
        repo, issueid, last_comment_id, title = parse_asana_ticket_name(task['name'])
        if repo not in tasks.keys():
            tasks[repo] = {}
        tasks[repo].update(
            {
                issueid: {
                    "last_comment_id": last_comment_id,
                    "task": task
                }
            }
        )
    return tasks

'''
Takes a Github user object and validates if they are a member of the org
'''
def user_in_org(user, org_login):
    for org in user.get_orgs():
        if org.login == org_login:
            return True
    return False 

'''
Pull issues from every github repo in 'repos', going back as many days as 
look_back_days specifies. Returns a list of issues with their comment strings
{
    <repo_name>: [
        <issue_title>: string
        <updated_on>: datetime
        <description>: string
        <last_coment>: string
    ]
}
'''
def pull_issues_from_github(github_client, repos, lookback_days, team_org):
    oldest_date = datetime.now()-timedelta(days=lookback_days)
    issues = {}
    for repo in repos:
        grepo = github_client.get_repo(repo)
        open_issues = grepo.get_issues(state='open')
        issues[grepo.name] = {
            'issues':  []
        }
        for issue in open_issues:
            if ((oldest_date - issue.updated_at).days <0):
                
                comments = issue.get_comments()
                url = issue.html_url
                print(url)
                description = issue.body

                issue_struct = {
                    'title': issue.title,
                    'updated_on': issue.updated_at,
                    'description': issue.body,
                    'url': url,
                    'id': str(issue.id)
                }

                if issue.comments >= 1:
                    #Only pull issues where the last commentor was not a team member
                    last_comment = comments.reversed[0]
                    last_commenter = last_comment.user
                    if not user_in_org(last_commenter, team_org):
                        issue_struct['last_comment'] = {
                                "user": last_commenter.login,
                                "body": last_comment.body,
                                "id": str(last_comment.id)
                        }
                        issues[grepo.name]['issues'].append(issue_struct)
                else:
                    issues[grepo.name]['issues'].append(issue_struct)

    return issues

def dump_issues_to_asana(asana_client, issues, project_gid):

    #Check for existing tickets
    existing_issues = get_asana_tasks(asana_client, project_gid)
    for repo in issues:
        for issue in issues[repo]['issues']:
            #If ticket exists skip, or add existing ticket so it gets updated
            if repo in existing_issues and issue['id'] in existing_issues[repo].keys():
                ex_issue = existing_issues[repo][issue['id']]
                if not issue.get('last_comment'):
                    continue
                elif ex_issue['last_comment_id'] == issue['last_comment']['id']:
                    continue
                else:
                    issue['existing_task'] = ex_issue['task']

            task_name = "{}-[{}-{}]- {}".format(repo, issue['id'], str(issue['last_comment']['id'] if issue.get('last_comment') else "NEW"), issue['title'])
            task_fields = {
                'name': task_name,
                'notes':
                    'Title: '+issue['title']+' '+issue['url']+'\n'+
                    'Last Updated: '+str(issue['updated_on'])+'\n'+
                    'Description: '+issue['description'],
                'projects': [ASANA_PROJECT_GID],
                
            }
            if issue.get('existing_task'):
                #if a task exists, remove the redundant properties and update the status to incomplete
                task_fields.pop('projects')
                task_fields['completed'] = False
                task = asana_client.tasks.update(issue['existing_task']['gid'], task_fields)
            else:
                task = asana_client.tasks.create(task_fields)
            #add last comment as a comment on story
            if issue.get('last_comment') and issue['last_comment']['id']:
                asana_client.stories.create_story_for_task(
                    task['gid'],
                    {
                        'text': 
                            'User: '+issue['last_comment']['user']+'\n'+
                            issue['last_comment']['body']
                    }
                )
            
            

def main():
    #Get any updated issues from Github
    github_client = get_github_client(GITHUB_TOKEN)
    issues = pull_issues_from_github(github_client, REPOS, LOOKBACK, TEAM_GITHUB_ORG)
    #Dump the issues into an Asana board
    asana_client = get_asana_client(ASANA_TOKEN)
    dump_issues_to_asana(asana_client, issues, ASANA_PROJECT_GID)

if __name__=='__main__':
    main()
    