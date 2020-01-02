print('Getting accesss rules')
acl_result = service.acl().list(calendarId='email').execute()
for rule in acl_result.get("items", []):
    print(rule)
