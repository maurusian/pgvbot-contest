import pywikibot
from datetime import datetime

def get_earliest_edit_after(page, username, given_date):
    # Convert the given_date string to a datetime object
    #given_date = datetime.fromisoformat(given_date)

    revisions = list(page.revisions(reverse=True))

    #print(revisions[0].size)

    # Filter out revisions made by the user after the given_date
    user_revisions = [rev for rev in revisions if rev.user == username and rev.timestamp >= given_date]

    if not user_revisions:
        return given_date, 0

    earliest_user_revision = user_revisions[0]  # Since the list is reversed, the earliest revision is the last one

    print(earliest_user_revision)

    if 'mw-reverted' in earliest_user_revision['tags']:
        return earliest_user_revision.timestamp, 0

    # Find the revision right before the earliest user revision
    prev_index = revisions.index(earliest_user_revision) - 1
    if prev_index >= 0:  # Check if there's a revision before this
        prev_revision = revisions[prev_index]
        diff = earliest_user_revision.size - prev_revision.size
    else:  # The user's revision is the first revision of the page
        diff = earliest_user_revision.size

    # Convert the timestamp back to a string in ISO 8601 format
    return earliest_user_revision.timestamp, diff
'''
#user_name = "مصطفى ملو"
user_name = "Dahmani mustafa"

site = pywikibot.Site("ar","wikipedia")

user = pywikibot.User(site, user_name)

START_DATE = '2023-04-25 00:00:00'

start_date = datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')

count = 0
for edit in user.contributions(total=500,reverse=True):  # set total to 500 as we only care if user has 500 edits or more
    #print(edit)
    #break
    if edit[2] < start_date:
        count += 1
        if count == 500:
            break
    else:
        break

print(count)

#title = "شمعون أزولاي"
#title = "ماكس كوهين أوليفار"
#title = "فقاص"
title = "قراشل (معجنات)"

page = pywikibot.Page(site,title)


print(get_earliest_edit_after(page, user_name, start_date))
'''

string = "Samira Guarnaouy"
print(string, string.capitalize(), string.lower(), string.upper())
