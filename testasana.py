import asana

client = asana.Client.access_token(ASANA_TOKEN)


ASANA_PROJECT_GID = '1173676030516145'
ASANA_WORKSPACE_GIT = '1141277692235279'


for task in client.tasks.find_by_project(ASANA_PROJECT_GID):
    print(task)