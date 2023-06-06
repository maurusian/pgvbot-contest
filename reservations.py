import pywikibot, json, re, sys, ast
from datetime import datetime, timedelta
import help_functions as hf
import ipaddress
from copy import deepcopy
from pywikibot import Timestamp
from operator import itemgetter


JSON_SITE_LANG = {"ar":"ary","ary":"ary","shi":"shi"}


# Constants
START_DATE = '2023-04-25 00:00:00'
END_DATE = '2023-06-10 23:59:59'


def get_total_edits(user_name):
    site = pywikibot.Site()
    user = pywikibot.User(site, user_name)
    
    # Convert start_date from string to datetime object
    start_date = datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')

    count = 0
    for edit in user.contributions(total=500,reverse=True):  # set total to 500 as we only care if user has 500 edits or more
        if edit[2] < start_date:
            count += 1
            if count == 500:
                break
        else:
            break

    return count

def generate_wiki_ranking_table(data, headers):
    table = '{| class="wikitable" style="margin:auto" \n|-\n! ' + ' !! '.join(headers)
    for row in data:
        table += '\n|-\n| ' + ' || '.join(str(cell) for cell in row)
    table += '\n|}'
    return table

def separate_and_rank_users_non_ar(users_data, root_participant_link):
    contributors = []

    for user, values in users_data.items():
        #total_edits = get_total_edits(user)
        participant_link = f'[[{root_participant_link}/{user}|{user}]]'
        contributors.append([participant_link, values["total_articles"], values["total_user_contributions"], values["total_no_issues_articles"], values["total_points"]])

    contributors.sort(key=itemgetter(4, 2, 3, 1), reverse=True)

    # add rank to the beginning of each user's data
    for i in range(len(contributors)):
        contributors[i].insert(0, i+1)

    # create wiki tables
    rank_str               = json_data["translations"]["ranking"]["rank_str"]
    user_str               = json_data["translations"]["ranking"]["user_str"]
    articles_str           = json_data["translations"]["ranking"]["articles_str"]
    no_issues_articles_str = json_data["translations"]["ranking"]["no_issue_articles_str"]
    contrib_str            = json_data["translations"]["ranking"]["contrib_str"]
    points_str             = json_data["translations"]["ranking"]["points_str"]
    
    headers = [rank_str, user_str, articles_str, contrib_str, no_issues_articles_str, points_str]
    contributors_table = generate_wiki_ranking_table(contributors, headers)
    
    return contributors_table
    
    

def separate_and_rank_users_ar(users_data, root_participant_link):
    beginners = []
    advanced = []

    
    
    # separate users into beginners and advanced
    for user, values in users_data.items():
        total_edits = get_total_edits(user)
        participant_link = f'[[{root_participant_link}/{user}|{user}]]'
        if total_edits < 500:
            beginners.append([participant_link, values["total_articles"], values["total_user_contributions"], values["total_no_issues_articles"], values["total_points"]])
        else:
            advanced.append([participant_link, values["total_articles"], values["total_user_contributions"], values["total_no_issues_articles"], values["total_points"]])
    
    # sort and rank users by total_points, total_contributions and total_articles respectively
    beginners.sort(key=itemgetter(4, 2, 3, 1), reverse=True)
    advanced.sort(key=itemgetter(4, 2, 3, 1), reverse=True)
    
    # add rank to the beginning of each user's data
    for i in range(len(beginners)):
        beginners[i].insert(0, i+1)
    for i in range(len(advanced)):
        advanced[i].insert(0, i+1)

    # create wiki tables
    rank_str               = json_data["translations"]["ranking"]["rank_str"]
    user_str               = json_data["translations"]["ranking"]["user_str"]
    articles_str           = json_data["translations"]["ranking"]["articles_str"]
    no_issues_articles_str = json_data["translations"]["ranking"]["no_issue_articles_str"]
    contrib_str            = json_data["translations"]["ranking"]["contrib_str"]
    points_str             = json_data["translations"]["ranking"]["points_str"]
    
    headers = [rank_str, user_str, articles_str, contrib_str, no_issues_articles_str, points_str]
    beginners_table = generate_wiki_ranking_table(beginners, headers)
    advanced_table = generate_wiki_ranking_table(advanced, headers)
    
    return beginners_table, advanced_table

def yes_no(boolean_value,json_data):
    return json_data["translations"]["yes"] if boolean_value else json_data["translations"]["no"]

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

    if 'mw-reverted' in earliest_user_revision['tags']:
        return earliest_user_revision.timestamp, 0

    #print(earliest_user_revision.size)

    # Find the revision right before the earliest user revision
    prev_index = revisions.index(earliest_user_revision) - 1
    if prev_index >= 0:  # Check if there's a revision before this
        prev_revision = revisions[prev_index]
        diff = earliest_user_revision.size - prev_revision.size
    else:  # The user's revision is the first revision of the page
        diff = earliest_user_revision.size

    # Convert the timestamp back to a string in ISO 8601 format
    return earliest_user_revision.timestamp, diff

def get_contributions_during_timeframe(page, username, start_datetime, end_datetime):

    actual_start_date, initial_diff = get_earliest_edit_after(page, username, start_datetime)

    revisions = list(page.revisions(reverse=True, starttime=actual_start_date, endtime=end_datetime))

    #initialize with the size of the first edit by the user

    user_contributions = initial_diff
    total_contributions = initial_diff

    for i in range(len(revisions) - 1):
        current_revision = revisions[i]
        next_revision = revisions[i + 1]
        size_diff = next_revision.size - current_revision.size

        print("comparing revision users",next_revision.user,username,size_diff)
        if next_revision.user.lower() == username.lower():
            if 'mw-reverted' not in next_revision['tags']:
                user_contributions += size_diff

        # Calculate total contributions in the given timeframe
        total_contributions += size_diff

    # Include the first revision's size in the user's contributions if they are the author
    print("revisions[0].size",revisions[0].size)
    
    
    return user_contributions, total_contributions

# Helper functions
def get_article_size(page):
    return page.latest_revision.size

def has_template(page):
    return any('{{' in line for line in page.text.splitlines())

def get_unique_references(page):
    unique_references = set()
    for ref in page.extlinks():
        unique_references.add(ref)
    return unique_references

def has_pictures_or_videos(page):
    return bool(page.imagelinks())

def has_issues(page, site, json_data):
    top_maintenance_cat_title = json_data["translations"]["categories"]["top_maintenance_cat"]
    top_maintenance_cat = pywikibot.Category(site, top_maintenance_cat_title)

    #orphaned cats are an exception to maintenance cats
    all_orphan_cat = json_data["translations"]["categories"]["all_orphan_cat"]
    orphan_cat_part = json_data["translations"]["categories"]["orphan_cat_part"]
    """
    #not gonna work since this category contains only categories
    if page in top_maintenance_cat.articles():
        return True
    """

    for cat in page.categories():
        if top_maintenance_cat in cat.categories() and cat.title() != all_orphan_cat and orphan_cat_part not in cat.title():
            return True
        for supercat in cat.categories():
            if top_maintenance_cat in supercat.categories() and supercat.title() != all_orphan_cat and orphan_cat_part not in supercat.title():
                return True
            
    return False

def get_points(user_contributions, total_contributions, qid, qcode_dict, references, has_media, has_template, page_has_issues):
    points = 0
    

    if user_contributions < 4000 or min(user_contributions, total_contributions) < 4000:
        return 0

    if page_has_issues:
        return 0

    points += 5

    if qid in qcode_dict.keys():
        points += 5

    points += (user_contributions // 4000) * 5

    if len(references) >= 3:
        points += 2

    if has_media:
        points += 1
    
    if has_template:
        points += 1

    return points

def generate_wiki_table(lang, username, qids, qcode_dict, site, json_data):
    start_datetime = datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')
    end_datetime = datetime.strptime(END_DATE, '%Y-%m-%d %H:%M:%S')

    site = pywikibot.Site(lang, 'wikipedia')

    count_str          = f'{json_data["translations"]["points"]["count"]}'
    article_str        = f'{json_data["translations"]["points"]["Article"]}'
    topic_str          = f'{json_data["translations"]["points"]["Topic"]}'
    user_contrib_size  = f'{json_data["translations"]["points"]["user_contrib_size"]}'
    total_contrib_size = f'{json_data["translations"]["points"]["total_contrib_size"]}'
    has_template_str   = f'{json_data["translations"]["points"]["has_template"]}'
    three_ref          = f'{json_data["translations"]["points"]["three_ref"]}'
    has_picture_str    = f'{json_data["translations"]["points"]["has_picture"]}'
    has_issues_str     = f'{json_data["translations"]["points"]["has_issues"]}'
    points_str         = f'{json_data["translations"]["points"]["points"]}'
    bytes_str          = f'{json_data["translations"]["points"]["bytes"]}'

    # Header
    table = '{| class="wikitable sortable"\n'
    table += f'! {count_str} !! {article_str} !! {topic_str} !! {user_contrib_size} ({bytes_str}) !! {total_contrib_size} ({bytes_str}) !! {has_template_str} !! {three_ref} !! {has_picture_str} !! {has_issues_str} !! {points_str}\n'

    i = 1
    total_points = 0
    total_articles = 0
    total_user_contributions = 0
    total_no_issues_articles = 0
    for qid in qids:
        item = pywikibot.ItemPage(site.data_repository(), qid)
        try:
            article_title = item.getSitelink(site)
            page = pywikibot.Page(site, article_title)

            user_contributions, total_contributions = get_contributions_during_timeframe(page, username, start_datetime, end_datetime)

            # Extract information
            topic = qcode_dict[qid][0]['topic']
            topic_with_link = f'[[{json_data["pages"]["main_page"]}/{json_data["pages"]["topics"]["main_topic_page"]}/{topic}|{topic}]]'
            article_size = get_article_size(page)
            if total_contributions == 0:
                percentage = 0
            else:
                percentage = round((user_contributions / total_contributions) * 100, 2)
            article_has_template = has_template(page)
            unique_references = get_unique_references(page)
            has_media = has_pictures_or_videos(page)
            page_has_issues = has_issues(page, site, json_data)
            points = get_points(user_contributions, total_contributions, qid, qcode_dict, unique_references, has_media, article_has_template, page_has_issues)

            total_points+=points

            total_articles+=1
            total_user_contributions+=user_contributions

            if not page_has_issues:
                total_no_issues_articles+=1

            # Append row to the table
            table += f'|-\n'
            table += f'| {i} || [[{article_title}]] ({article_size}) || {topic_with_link} || {user_contributions} ({percentage}%) || {total_contributions} || {yes_no(article_has_template, json_data)} || {yes_no(len(unique_references) >= 3, json_data)} || {yes_no(has_media, json_data)} || {yes_no(page_has_issues, json_data)} || {points}\n'
        except pywikibot.exceptions.NoPageError:
            continue
        i+=1
    table += '|}\n'
    return table, total_points, total_articles, total_user_contributions, total_no_issues_articles


def is_ip_address(username):
    try:
        ipaddress.ip_address(username)
        return True
    except ValueError:
        return False

"""
#moved to help functions
def read_json_file(site, json_page_title):
    json_page = pywikibot.Page(site, json_page_title)
    json_content = json_page.get()
    return json.loads(json_content)
"""

# Function to extract the user name(s) from the line
def get_user_names_from_line(line, unsigned_template_name, user_namespace, user_template_name):
    user_names = re.findall(r'\[\[(?:' + re.escape(user_namespace) + r'|User):([^|\]]+)\|', line, flags=re.IGNORECASE)
    #print(user_names)
    if not user_names:
        unsigned_match = re.search(r'{{' + re.escape(unsigned_template_name) + r'\|1=([^|}]+)', line)
        if unsigned_match:
            user_names.append(unsigned_match.group(1))
        if not user_names:
            user_names = re.findall(r"{{" + re.escape(user_template_name) + r"\|(.*?)}}", line, flags=re.IGNORECASE)
        if user_names:
            return list(set(user_names))
    else:
        return list(set(user_names))
    
    return None

# Function to extract the date from the line
def get_date_from_line(line, month_names):
    # Replace placeholders with actual month names in the date regex pattern
    month_names_pattern = '|'.join(month_names)
    date_pattern = r'(\d{1,2}):(\d{2})، (\d{1,2}) (' + month_names_pattern + r') (\d{4})'
    
    match = re.search(date_pattern, line)
    if match:
        hour, minute, day, month_name, year = match.groups()
        month = month_names.index(month_name) + 1
        return datetime(int(year), month, int(day), int(hour), int(minute))
    else:
        return None

# Function to extract the reserved topics (Qcodes) as a list
def get_reserved_topics_from_line(line):
    qcodes = re.findall(r'\b(q\d+)\b', line, flags=re.IGNORECASE)
    return [qcode.upper() for qcode in qcodes]


def write_notifications(site,notification_list,notification_page_title,save_message):
    notification_page = pywikibot.Page(site,notification_page_title)
    temp = notification_page.text
    for notification in notification_list:
        if notification not in temp:
            temp.text += '\n*'+notification+'--~~~~'

    if temp != notification_page.text:
        notification_page.text = temp
        notification_page.save(save_message)

"""
#moved to help functions
def load_participants(site,json_data):
    username_pattern = r'\{\{مس\|([^}]+)\}\}'
    participants_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['participants_page']}"
    participants_page = pywikibot.Page(site,participants_page_title)
    
    usernames = re.findall(username_pattern, participants_page.text)

    # Filter out any non-matching usernames, like "-"
    filtered_usernames = [username for username in usernames if username != '-']

    return filtered_usernames
"""

def process_raw_reservations(site,json_data):
    reservation_section_title = f"{json_data['reservation_section_title']}"
    raw_reservations = {'user_reservations':{},'anonymous_reservations':{},'unsigned_reservations':{}}
    pretreated_raw_reservations = {'user_reservations':{},'anonymous_reservations':{}}
    discarded_lines = []
    main_topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}"

    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_male_namespace = json_data['translations']['namespaces']['user_male']
    user_female_namespace = json_data['translations']['namespaces']['user_female']
    user_template_name = json_data['translations']['templates']['user_template']
    
    for subpage_title in json_data['pages']['topics']['subpages']:
        topic_page = pywikibot.Page(site,f"{main_topic_page_title}/{subpage_title}")
        #print(topic_page.title())
        #print(subpage_title)
        #print(reservation_section_title)
        reservation_section = hf.get_section_by_title(topic_page.text, reservation_section_title)
        #print(reservation_section)
        if reservation_section is not None:
            reservation_lines = hf.remove_empty_lines(reservation_section)
            for line in reservation_lines:
                if line.strip() != "" and line.strip() != "=== "+json_data["reservation_section_title"]+" ===":
                    usernames = get_user_names_from_line(line, unsigned_template_name, user_male_namespace, user_template_name)

                    if usernames is None:
                        usernames = get_user_names_from_line(line, unsigned_template_name, user_female_namespace, user_template_name)
                        
                    jury = json_data['jury']
                    organizers = json_data['organizers']
                    bot = json_data['bot']
                    if usernames is not None:
                        if len(usernames) == 1:
                            username = usernames[0]
                        elif usernames[-1] in jury or usernames[-1] in organizers:
                            username = usernames[-1]
                        else:
                            username = usernames[0]
                        if username not in jury and username not in organizers and username != bot:
                        
                            line_index = reservation_lines.index(line)
                            ignore_line = False
                            next_line = None
                            if line_index < len(reservation_lines)-1:
                                next_line = reservation_lines[line_index+1]

                                next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_male_namespace, user_template_name)

                                if next_usernames is None:
                                    next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_female_namespace, user_template_name)
                                #print(username)
                                #print(next_username)
                                if next_usernames is not None:
                                    if len(next_usernames) == 1:
                                        next_username = next_usernames[0]
                                    elif next_usernames[-1] in jury or next_usernames[-1] in organizers or next_username == bot:
                                        next_username = next_usernames[-1]
                                    else:
                                        next_username = next_usernames[0]
                                    if next_username in jury or next_username in organizers or next_username == bot:
                                        
                                        ignore_line = True
                            if not ignore_line:
                                #print(username)
                                month_names = json_data['months']
                                date = get_date_from_line(line,month_names)
                                #print(date)
                                reserved_topics = get_reserved_topics_from_line(line)
                                #print(reserved_topics)
                                if '/' in username:
                                    username = username.split('/')[-1]
                                if is_ip_address(username):
                                    if username not in raw_reservations['anonymous_reservations'].keys():
                                        raw_reservations['anonymous_reservations'][username] = {subpage_title:[{'reservation':line,'answer':f"{json_data['reservation_answers']['no_anonymous']}"}]}
                                    else:
                                        if subpage_title not in raw_reservations['anonymous_reservations'][username].keys():
                                            raw_reservations['anonymous_reservations'][username][subpage_title] = [{'reservation':line,'answer':f"{json_data['reservation_answers']['no_anonymous']}"}]
                                        else:
                                            raw_reservations['anonymous_reserations'][username][subpage_title].append({'reservation':line,'answer':f"{json_data['reservation_answers']['no_anonymous']}"})
                                else:
                                    if username not in raw_reservations['user_reservations'].keys():
                                        raw_reservations['user_reservations'][username] = {subpage_title:[{'reservation':line,'reserved_topics':reserved_topics,'date':date}]}
                                    else:
                                        if subpage_title not in raw_reservations['user_reservations'][username].keys():
                                            raw_reservations['user_reservations'][username][subpage_title] = [{'reservation':line,'reserved_topics':reserved_topics,'date':date}]
                                        else:
                                            raw_reservations['user_reservations'][username][subpage_title].append({'reservation':line,'reserved_topics':reserved_topics,'date':date})
                            else:

                                #ignored reservation must still be checked if they were added to the table or not, or if they should be removed, depending on the response
                                #month_names = json_data['months']
                                #date = get_date_from_line(line,month_names)
                                reserved_topics = get_reserved_topics_from_line(line)
                                if '/' in username:
                                    username = username.split('/')[-1]
                                if is_ip_address(username):
                                    if username not in pretreated_raw_reservations['anonymous_reservations'].keys():
                                        pretreated_raw_reservations['anonymous_reservations'][username] = {subpage_title:[{'reservation':line
                                                                                                                           ,'next_line':next_line
                                                                                                                           ,'reserved_topics':reserved_topics}]}
                                    else:
                                        if subpage_title not in pretreated_raw_reservations['anonymous_reservations'][username].keys():
                                            pretreated_raw_reservations['anonymous_reservations'][username][subpage_title] = [{'reservation':line
                                                                                                                               ,'next_line':next_line
                                                                                                                               ,'reserved_topics':reserved_topics}]
                                        else:
                                            pretreated_raw_reservations['anonymous_reserations'][username][subpage_title].append({'reservation':line
                                                                                                                                  ,'next_line':next_line
                                                                                                                                  ,'reserved_topics':reserved_topics})
                                else:
                                    month_names = json_data['months']
                                    date = get_date_from_line(line,month_names)
                                    if username not in pretreated_raw_reservations['user_reservations'].keys():
                                        pretreated_raw_reservations['user_reservations'][username] = {subpage_title:[{'reservation':line
                                                                                                                      ,'next_line':next_line
                                                                                                                      ,'reserved_topics':reserved_topics
                                                                                                                      ,'date':date}]}
                                    else:
                                        if subpage_title not in pretreated_raw_reservations['user_reservations'][username].keys():
                                            pretreated_raw_reservations['user_reservations'][username][subpage_title] = [{'reservation':line
                                                                                                                          ,'next_line':next_line
                                                                                                                          ,'reserved_topics':reserved_topics
                                                                                                                          ,'date':date}]
                                        else:
                                            pretreated_raw_reservations['user_reservations'][username][subpage_title].append({'reservation':line
                                                                                                                              ,'next_line':next_line
                                                                                                                              ,'reserved_topics':reserved_topics
                                                                                                                              ,'date':date})
                            
                    elif username not in jury and username not in organizers and username != bot:
                        #treat untreated unsigned reservations, treated unsigned reservations (followed by a response from an organizer or jury member are completely ignored)
                        line_index = reservation_lines.index(line)
                        ignore_line = False
                        next_line = None
                        if line_index < len(reservation_lines)-1:
                            next_line = reservation_lines[line_index+1]
                            next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_male_namespace, user_template_name)

                            if next_usernames is None:
                                next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_female_namespace, user_template_name)
                            #print(username)
                            #print(next_username)
                                
                            if next_usernames is not None:
                                if len(next_usernames) == 1:
                                    next_username = next_usernames[0]
                                elif next_usernames[-1] in jury or next_usernames[-1] in organizers:
                                    next_username = next_usernames[-1]
                                else:
                                    next_username = next_usernames[0]
                                if next_username in jury or next_username in organizers or next_username == bot:
                                            
                                    ignore_line = True
                                
                        if not ignore_line:
                            reserved_topics = get_reserved_topics_from_line(line)
                            if reserved_topics is not None and len(reserved_topics)>0:
                                if subpage_title not in raw_reservations['unsigned_reservations'].keys():
                                    raw_reservations['unsigned_reservations'][subpage_title] = [line]
                                else:
                                    raw_reservations['unsigned_reservations'][subpage_title].append(line)
                            else:
                                #lines that do not contain any clearly relevant information
                                discarded_lines.append(line)
                        
    return raw_reservations, pretreated_raw_reservations, discarded_lines




def get_topic_qcodes(site,topics_tables):
    return hf.extract_qcodes(topics_tables)

def convert_topics_tables_to_dicts(topics_tables,json_data):
    #a deepy copy is needed to ensure the objects don't refer to the same address
    dictionarized_topics_tables = deepcopy(topics_tables)
    qcode_dict = {}
    rownum_colname = json_data['translations']['row_number']
    for topic, section in topics_tables.items():
        #print(topic)
        for section_title, content in section.items():
            #print(section_title)
            for subsection_title, subsection_content in content.items():
                print(section_title)
                print(subsection_title)
                new_topic_table = hf.parse_wikipedia_table(subsection_content,0)
                
                dictionarized_topics_tables[topic][section_title][subsection_title] = new_topic_table
                for i in range(len(new_topic_table)):
                    qcode = hf.extract_qcodes(new_topic_table[i][json_data["translations"]["topic"]])[0]
                    #adjusting table row numbers
                    dictionarized_topics_tables[topic][section_title][subsection_title][i][rownum_colname] =  str(i+1)
                    if qcode not in qcode_dict.keys():
                        rownum = i
                        qcode_dict[qcode] = [{"topic":topic
                                              ,"section_title":section_title
                                              ,"subsection_title":subsection_title
                                              ,"rownum":rownum
                                              ,"reservation":new_topic_table[i][json_data["translations"]["reservation_status"]]}]
                    else:
                        qcode_dict[qcode].append({"topic":topic
                                                  ,"section_title":section_title
                                                  ,"subsection_title":subsection_title
                                                  ,"rownum":rownum
                                                  ,"reservation":new_topic_table[i][json_data["translations"]["reservation_status"]]})
                    
                #print(type(dictionarized_topics_tables[topic][section_title][subsection_title][0]))

    return dictionarized_topics_tables, qcode_dict
        

def load_topics_tables(site,json_data):
    main_page = f"{json_data['pages']['main_page']}"
    #print(main_page)
    main_topic_page = f"{main_page}/{json_data['pages']['topics']['main_topic_page']}"
    #print(main_topic_page)
    topic_subpage_names = ast.literal_eval(f"{json_data['pages']['topics']['subpages']}")
    #print(topic_subpage_names)
    topics_tables_dict = {}
    for subpage_name in topic_subpage_names:
        subpage_ttl = f"{main_topic_page}/{subpage_name}"
        #print(subpage_ttl)
        subpage = pywikibot.Page(site,subpage_ttl)
        topics_tables_dict[subpage_name] = hf.get_section_contents(subpage,json_data)

    return topics_tables_dict


def write_to_notification_page(notifications,notifications_page,json_data):
    SAVE_MESSAGE = f"{json_data['SAVE_MESSAGES_DICT']['NOTIFY']}"
    try:
        notifications_page.text+='\n'+notifications
        notifications_page.save(SAVE_MESSAGE)
    except:
        print("Could not save to notification page.")
        print(sys.exc_info())

def process_answers(answers,json_data):
    #print("answers len:",len(answers.values()))
    if len(set(answers.values())) == 1:
        if list(answers.values())[0] == "accepted":
            return json_data['reservation_answers']['accepted_reservation']
        elif list(answers.values())[0] == "expired":
            return json_data['reservation_answers']['cancel_reservation_not_modified']
        elif list(answers.values())[0] == "inexistent":
            return json_data['reservation_answers']['cancel_inexistent_topic']
        else:
            print("UNKNOWN response type")

    AND = f" {json_data['translations']['AND']} "
    return (json_data['reservation_answers']['mixed_answer']
        .replace("{rejected}", AND.join([key for key, value in answers.items() if value == "expired" or value == "inexistent"]))
        .replace("{accepted}", AND.join([key for key, value in answers.items() if value == "accepted"])))

def is_not_valid_participant(user,participants,jury,organizers,bot):
    lower_participants = [participant.lower() for participant in participants]
    lower_organizers = [organizer.lower() for organizer in organizers]
    lower_jury = [member.lower() for member in jury]
    lower_bot = bot.lower()

    lower_user = user.lower()

    return (lower_user not in lower_participants and lower_user not in lower_jury and lower_user not in lower_organizers and lower_user != lower_bot)

def get_user_reservations_from_table(dictionarized_topics_tables,json_data):
    raw_table_reservations = {"user_reservations":{},"anonymous_reservations":{},"improper_reservations":[]}

    topic_colname = json_data['translations']['topic']
    #print(topic_colname)
    resrv_colname = json_data['translations']['reservation_status']

    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_male_namespace = json_data['translations']['namespaces']['user_male']
    user_female_namespace = json_data['translations']['namespaces']['user_female']

    user_template_name = json_data['translations']['templates']['user_template']

    for topic, section in dictionarized_topics_tables.items():
        #print(topic)
        for section_title, content in section.items():
            #print(section_title)
            for subsection_title, table in content.items():
                #print(table[0].keys())
                for i in range(len(table)):
                    #print(topic, section_title, subsection_title, i)
                    
                    if table[i][resrv_colname].strip() != "":
                        usernames = get_user_names_from_line(table[i][resrv_colname], unsigned_template_name, user_male_namespace, user_template_name)

                        if usernames is None:
                            usernames = get_user_names_from_line(table[i][resrv_colname], unsigned_template_name, user_female_namespace, user_template_name)
                        if usernames is None or len(usernames) == 0:
                            #add to improper / No username
                            raw_table_reservations["improper_reservations"].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname].strip()
                                                                                    ,"reason":"nouser"
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                        elif len(usernames)>1:
                            raw_table_reservations["improper_reservations"].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname].strip()
                                                                                    ,"reason":"multiple"
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                        else:
                            #further checks
                            username = usernames[0]
                            if '/' in username:
                                username = username.split('/')[-1]
                            if is_ip_address(username):
                                if username in raw_table_reservations["anonymous_reservations"].keys():
                                    
                                    raw_table_reservations["anonymous_reservations"][username].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname]
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                                else:
                                    raw_table_reservations["anonymous_reservations"][username] = [{"topic":topic
                                                                                                ,"section_title":section_title
                                                                                                ,"subsection_title":subsection_title
                                                                                                ,"rownum":i
                                                                                                ,"reservation_line":table[i][resrv_colname].strip()
                                                                                                ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]}]
                            else:
                                #get date
                                month_names = json_data['months']
                                date = get_date_from_line(table[i][resrv_colname],month_names)
                                if date is not None:
                                    if username in raw_table_reservations["user_reservations"].keys():
                                        
                                        raw_table_reservations["user_reservations"][username].append({"topic":topic,"section_title":section_title
                                                                                        ,"subsection_title":subsection_title,"rownum":i
                                                                                        ,"reservation_line":table[i][resrv_colname].strip()
                                                                                        ,'date':date
                                                                                        ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                                    else:
                                        raw_table_reservations["user_reservations"][username] = [{"topic":topic,"section_title":section_title
                                                                                        ,"subsection_title":subsection_title,"rownum":i
                                                                                        ,"reservation_line":table[i][resrv_colname].strip()
                                                                                        ,'date':date
                                                                                        ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]}]
                                else:
                                    raw_table_reservations["improper_reservations"].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname].strip()
                                                                                    ,"reason":"nodate"
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})

    return raw_table_reservations


def get_inline_reservation_line_from_table_reservation(table_reservation_line,qcode,json_data):
    underway_template = "{{"+f"{json_data['translations']['templates']['underway_template']}"+"}}"
    completed_template = "{{"+f"{json_data['translations']['templates']['completed_template']}"+"}}"
    contrib_size_template = f"{json_data['translations']['templates']['contrib_size_template']}"
    inline_reservation_line = table_reservation_line.replace(underway_template,"").replace(completed_template,"")
    inline_reservation_line = re.sub(r'\{\{'+contrib_size_template+'\|[^{}]*\}\}', '', inline_reservation_line)

    return f"({qcode}) {inline_reservation_line}"


#TODO, develop this function
def get_table_reservation_line_from_inline_reservation(inline_reservation_line,qcode,json_data,status):
    qcode_ptrn = r'\(Q\d+\)'
    underway_template = "{{"+f"{json_data['translations']['templates']['underway_template']}"+"}}"
    completed_template = "{{"+f"{json_data['translations']['templates']['completed_template']}"+"}}"
    #contrib_size_template = f"{json_data['translations']['templates']['contrib_size_template']}"
    table_reservation_line = inline_reservation_line.strip('#*: ')
    table_reservation_line  = re.sub(qcode_ptrn, '', table_reservation_line)
    #inline_reservation_line = re.sub(r'\{\{'+contrib_size_template+'\|[^{}]*\}\}', '', inline_reservation_line)

    if status == "underway":
        return underway_template + " " + table_reservation_line

    else:
        return completed_template + " " + table_reservation_line


def compare_reservations(line_reservation, tab_reservation):
    """
    Compares table and inline reservations on the same page for a specific user
    """
    
    if tab_reservation["reserved_code"] not in line_reservation["reserved_topics"]:
        return False
    if line_reservation["date"] is None and tab_reservation["date"] is not None:
        return False
    if line_reservation["date"] is not None and tab_reservation["date"] is None:
        return False
    if (line_reservation["date"] - tab_reservation["date"]) > timedelta(hours=24) or (tab_reservation["date"] - line_reservation["date"]) > timedelta(hours=24):
        return False

    return True

def find_inline_reservation(user_reservations, table_reservation, user, subpage_title):
    if user not in user_reservations.keys():
        return False
    if subpage_title not in user_reservations[user].keys():
        return False
    for line_reservation in user_reservations[user][subpage_title]:
        if compare_reservations(line_reservation, table_reservation):
            return True
    return False

def process_participants(participants, json_data, notifications_list):
    morocco_contest_cat = json_data['translations']['categories']['MOROCCO_CONTEST_CAT']
    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_male_namespace = json_data['translations']['namespaces']['user_male']
    user_female_namespace = json_data['translations']['namespaces']['user_female']
    user_template_name = json_data['translations']['templates']['user_template']
    for participant in participants:
        user = pywikibot.User(site, participant)
        try:
            if user.exists():
                user_page = user.getUserPage()
                #user_page
                if user_participating_full_template not in user_page.text and not hf.page_has_category(user_page, morocco_contest_cat, site):
                    user_page.text +='\n'+user_participating_full_template
                    #print(user_page.title())
                    user_page.save(json_data["SAVE_MESSAGES_DICT"]["ADD_USER_PARTICIPATING_TMPL_TO_USRPAGE"])
                    #print("adding to page",participant)
                else:
                    #user_page.text = user_page.text.replace(user_participating_full_template,"")
                    #user_page.save("تعديل مؤقت لتصحيح خطأ البوت")
                    #print("user",participant,"has the participatin tag")
                    continue
        except pywikibot.exceptions.InconsistentTitleError:
            participant_list_wplink = f'{json_data["pages"]["main_page"]}/{json_data["pages"]["participants_page"]}'
            #print(participant_list_wplink)
            notification = json_data["notifications"]["ERROR_UPDATING_USERPAGE"].format(participant=participant
                                                                                        , user_participating_full_template=user_participating_full_template
                                                                                        , user_namespace=user_male_namespace)
           
            #print(notification)
            if notification[:-4] not in notifications_page.text:
                notification_list.append(notification)
        except pywikibot.exceptions.OtherPageSaveError:
            participant_list_wplink = f'{json_data["pages"]["main_page"]}/{json_data["pages"]["participants_page"]}'
            #print(participant_list_wplink)
            notification = json_data["notifications"]["ERROR_UPDATING_USERPAGE"].format(participant=participant
                                                                                        , user_participating_full_template=user_participating_full_template
                                                                                        , user_namespace=user_male_namespace)
            #print(notification)
            if notification[:-4] not in notifications_page.text:
                notification_list.append(notification)
        """
        else:   
        
            participant_list_wplink = f'{json_data["pages"]["main_page"]}/{json_data["pages"]["participants_page"]}'
            print(participant_list_wplink)
            notification = json_data["notifications"]["PARTICIPANT_DOESNT_EXIST"].format(participant=participant, participant_list_wplink=participant_list_wplink)
            print(notification)
            if notification[:-4] not in notifications_page.text:
                notification_list.append(notification)
        """

    return notifications_list

def copy_reservation_to_table_row(qcode_dict):
    pass


def process_unprocessed_inline_reservations(raw_user_reservations
                                            , participants
                                            , json_data
                                            , topics_tables
                                            , dictionarized_topics_tables
                                            , qcode_dict
                                            , notification_list
                                            , pages_to_save):
    
    jury = json_data['jury']
    organizers = json_data['organizers']
    bot = json_data['bot']
    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_male_namespace = json_data['translations']['namespaces']['user_male']
    user_female_namespace = json_data['translations']['namespaces']['user_female']
    user_template_name = json_data['translations']['templates']['user_template']
    rewrite_table = False
    for user, reservations in raw_user_reservations.items():
        #print(user)
        subpage_title = list(reservations.keys())[0]
        subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
        formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
        
        if is_not_valid_participant(user,participants,jury,organizers,bot):
            #print(user)
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-4] not in notifications_page.text:
                notification_list.append(new_notification)

        else:
            #if user == "مصطفى ملو":
            #   print(user, reservations["مؤسسات"])
            for subpage_title, topic_reservations in reservations.items():
                print(subpage_title)
                answers = {}
                rewrite_table = False
                #if subpage_title == "مؤسسات": #to observe changes on a particular page
                if True:
                    #print(user)
                    #if user == "مصطفى ملو":
                    #    print(topic_reservations)
                    for topic_reservation in topic_reservations:
                        date = topic_reservation['date']
                        if date is not None:
                            #print(date)
                            #print(hf.is_more_than_one_day_old(date))
                            if hf.is_more_than_one_day_old(date):
                                #check if each reserved topic has been modified by the user in the alloted time
                                reserved_topics = topic_reservation['reserved_topics']
                                print(reserved_topics)
                                for qcode in reserved_topics:
                                    if qcode not in qcode_dict.keys():
                                        answers[qcode] = "inexistent"
                                    else:
                                        page = hf.get_wikipedia_page(qcode, lang)

                                        #print(qcode, page.title())

                                        if page is None:
                                            
                                            print(f"page for language {lang} with qcode {qcode} doesn't exist!")
                                            #cancel reservation
                                            answers[qcode] = "expired"
                                            
                                            #remove reservation from table if already there

                                            topic = qcode_dict[qcode][0]["topic"]
                                            section_title = qcode_dict[qcode][0]["section_title"]
                                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                            rownum = qcode_dict[qcode][0]["rownum"]
                                            print(qcode)
                                            print(subpage_title)
                                            print(section_title)
                                            print(resrv_colname)
                                            #print(dictionarized_topics_tables[subpage_title])
                            
                                            #print(dictionarized_topics_tables[subpage_title][section_title])
                                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum])
                                            table_reservation_line = dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname]
                                            if table_reservation_line != "":
                                                #check for conflict
                                                #print(table_reservation_line)
                                                table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_male_namespace, user_template_name)

                                                if table_reserving_users is None:
                                                    table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_female_namespace, user_template_name)
                                                    
                                                #dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                                if table_reserving_users is not None:
                                                    if table_reserving_users[0] != user:
                                                        subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                                        notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, subpage_link=subpage_link, subpage_title=subpage_title)
                                                        notification_list.append(notification)
                                                else:
                                                    dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname] = ""
                                                    rewrite_table = True
                                                    #print("rewrite table, remove")
                                        elif hf.user_modified_page_since(page, user, topic_reservation['date']):
                                            #copy to table(s) if not already done
                                            #but first check if there's no conflict reservation in table by another participant
                                            """
                                            for x in range(len(qcode_dict[qcode])):
                                                qcode_reservation = qcode_dict[qcode][x]["reservation"]
                                            """
                                            #approve reservation in-line
                                            answers[qcode] = "accepted"

                                            print(page.title())
                                            
                                            #save to user contribution dictionary
                                            """
                                            capitalized_user = hf.properly_capitalize(user)
                                            if capitalized_user in all_participants_contributions.keys():
                                                if qcode not in all_participants_contributions[capitalized_user]:
                                                    all_participants_contributions[capitalized_user].append(qcode)
                                                    
                                            else:
                                                all_participants_contributions[capitalized_user] = [qcode]
                                            """
                                            #copy to dictionarized_topics_tables
                                            if len(qcode_dict[qcode])>1:
                                                print(qcode)
                                            topic = qcode_dict[qcode][0]["topic"]
                                            section_title = qcode_dict[qcode][0]["section_title"]
                                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                            rownum = qcode_dict[qcode][0]["rownum"]
                                            table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                            print("test if reservation is on table for modified page")
                                            print(table_reservation_line)
                                            if table_reservation_line == "":
                                                dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                                #save table flag
                                                rewrite_table = True

                                                
                                                
                                                print("rewrite table, add")
                                            else:
                                                #check for conflict
                                                #if conflict:
                                                #print("Reservation conflict on page: {}")
                                                #notify
                                                table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_male_namespace, user_template_name)

                                                if table_reserving_users is None:
                                                    table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_female_namespace, user_template_name)

                                                table_reserving_user = table_reserving_users[0]
                                                    
                                                if table_reserving_user.lower() != user.lower():
                                                    subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                                    notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, subpage_link=subpage_link, subpage_title=subpage_title)
                                                    notification_list.append(notification)
                                            #print(f"page {page.title()} was modified by user {user}!")
                                        else:
                                            #else cancel reservation, and remove reservation from table if already there
                                            answers[qcode] = "expired"
                                            if len(qcode_dict[qcode])>1:
                                                print(qcode)
                                            topic = qcode_dict[qcode][0]["topic"]
                                            section_title = qcode_dict[qcode][0]["section_title"]
                                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                            rownum = qcode_dict[qcode][0]["rownum"]
                                            table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                            #print("test if reservation is on table for unmodified page")
                                            #print(table_reservation_line)
                                            if table_reservation_line != "":
                                                #check for conflict
                                                table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_male_namespace, user_template_name)

                                                if table_reserving_users is None:
                                                    table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_female_namespace, user_template_name)
                                                #dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                                if table_reserving_users is not None:
                                                    if table_reserving_users[0] != user:
                                                        subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                                        notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, subpage_link=subpage_link, subpage_title=subpage_title)
                                                        notification_list.append(notification)
                                                else:
                                                    dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname] = ""
                                                    rewrite_table = True
                                                    #print("rewrite table, remove")
                                            #print(f"page {page.title()} has not been modified by user {user}!")
                                #make sure to check for conflicting reservations
                                #print(topic_reservation['reservation'])
                                #print(topic_reservation['reserved_topics'])
                                
                            else:
                                reserved_topics = topic_reservation['reserved_topics']
                                for qcode in reserved_topics:
                                    if qcode not in qcode_dict.keys():
                                        answers[qcode] = "inexistent"
                                    else:
                                        page = hf.get_wikipedia_page(qcode, lang)

                                        if page is not None:
                                            if hf.user_modified_page_since(page, user, topic_reservation['date']):
                                                answers[qcode] = "accepted"

                                                print(page.title())
                                                
                                                #save to user contribution dictionary
                                                """
                                                capitalized_user = hf.properly_capitalize(user)
                                                if capitalized_user in all_participants_contributions.keys():
                                                    if qcode not in all_participants_contributions[capitalized_user]:
                                                        all_participants_contributions[capitalized_user].append(qcode)
                                                        
                                                else:
                                                    all_participants_contributions[capitalized_user] = [qcode]
                                                """
                                                #copy to dictionarized_topics_tables
                                                if len(qcode_dict[qcode])>1:
                                                    print(qcode)
                                                topic = qcode_dict[qcode][0]["topic"]
                                                section_title = qcode_dict[qcode][0]["section_title"]
                                                subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                                rownum = qcode_dict[qcode][0]["rownum"]
                                                table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                                print("test if reservation is on table for modified page")
                                                print(table_reservation_line)
                                                if table_reservation_line == "":
                                                    dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                                    #save table flag
                                                    rewrite_table = True
                                        else:
                                            #copy reservation to table row(s)
                                            print('printing qcode and content: ',qcode, qcode_dict[qcode])
                                            if len(qcode_dict[qcode])>1:
                                                print(qcode)
                                            topic = qcode_dict[qcode][0]["topic"]
                                            section_title = qcode_dict[qcode][0]["section_title"]
                                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                            rownum = qcode_dict[qcode][0]["rownum"]
                                            table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                            #print("test if reservation is on table for modified page")
                                            #print(table_reservation_line)
                                            if table_reservation_line == "":
                                                table_reservation_line = get_table_reservation_line_from_inline_reservation(topic_reservation['reservation'],qcode,json_data,"underway")
                                                dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = table_reservation_line
                                                #save table flag
                                                rewrite_table = True
                                                #print("rewrite table, add")
                                            else:
                                                #check for conflict
                                                #if conflict:
                                                #print("Reservation conflict on page: {}")
                                                #notify
                                                table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_male_namespace, user_template_name)

                                                if table_reserving_users is None:
                                                    table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_female_namespace, user_template_name)
                                                table_reserving_user = table_reserving_users[0]
                                                
                                                if table_reserving_user is not None and table_reserving_user[0].lower() != user.lower():
                                                    subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                                    notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, subpage_link=subpage_link, subpage_title=subpage_title)
                                                    notification_list.append(notification)
                                        
                        else:
                            #notify organizer
                            new_notification = f"{notifications['NO_RESERVATION_DATE']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
                            if new_notification[:-4] not in notifications_page.text:
                                notification_list.append(new_notification)
                            
                        

                    topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                    topic_page = pywikibot.Page(site,topic_page_title)
                    tmp_text = topic_page.text
                    if len(answers)>0:
                        
                        #answer = json_data['reservation_answers']['cancel_reservation_not_modified']
                        message = process_answers(answers,json_data)
                        INLINE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INLINE_RESERVATION_PROCESSING']
                        #print(user)
                        #print(message)
                        #print(topic_reservation['reservation'],f"{topic_reservation['reservation']}\n{message}")
                        #print(reserved_topics)
                        #print(topic_reservation['date'])
                        #print("adding topics page to save dict")
                        if topic_page in pages_to_save.keys():
                            pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topic_reservation['reservation'],f"{topic_reservation['reservation']}\n{message}")
                        else:
                            INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                            pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                            pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topic_reservation['reservation'],f"{topic_reservation['reservation']}\n{message}")

                    if rewrite_table:
                        print(subpage_title,section_title,subsection_title)
                 
                        updated_table = hf.list_of_dicts_to_wikitext_table(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                        #print(updated_table)
                        #print(topics_tables[topic][section_title][subsection_title])
                        #tmp_text = tmp_text.replace(topics_tables[topic][section_title][subsection_title],updated_table)
                        if topic_page in pages_to_save.keys():
                            pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)
                        else:
                            INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                            pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                            pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)
                    """      
                    if tmp_text != topic_page.text:
                        print("updating topics page")
                        INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                        topic_page.text = tmp_text
                        
                        topic_page.save(INTABLE_RESERVATION_PROCESSING)
                    """
                
            
        """
        if user in jury:
            notification_list.append(f"{notifications['NO_JURY_PARTICIPANTS']}")
        if user in organizers:
            notification_list.append(f"{notifications['NO_ORGANIZER_PARTICIPANTS']}")
        
        for qcode in reservations:
            if qcode not in topic_qcodes:
                notification_list.append(f"{notifications['TOPIC_NOT_ON_LIST']}")
        """
    return notification_list, pages_to_save

def process_raw_table_reservations(raw_table_user_reservations
                                   , participants
                                   , json_data
                                   , topics_tables
                                   , qcode_dict
                                   , dictionarized_topics_tables
                                   , notification_list
                                   , pages_to_save
                                   , all_participants_contributions):
    jury = json_data['jury']
    organizers = json_data['organizers']
    bot = json_data['bot']
    for user, reservations in raw_table_user_reservations.items():
        
        print(user)
        if is_not_valid_participant(user,participants,jury,organizers,bot):
            #print(user)
            subpage_title = reservations[0]["topic"]
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-4] not in notifications_page.text:
                notification_list.append(new_notification)

        else:
            for reservation in reservations:
                rewrite_table = False
                answers = {}
                subpage_title = reservation["topic"]
                print(subpage_title)
                #if subpage_title == "سياسة": # and subpage_title != "الأدب": #to observe changes on a particular page
                if True:
                    topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                    topic_page = pywikibot.Page(site,topic_page_title)
                    tmp_text = topic_page.text
                    if hf.is_more_than_one_day_old(reservation['date']):
                        #check if each reserved topic has been modified by the user in the alloted time
                        qcode = reservation['reserved_code']
                        #print(qcode)
                        page = hf.get_wikipedia_page(qcode, lang)
                        
                        if page is None:
                            
                            #print(f"page for language {lang} with qcode {qcode} doesn't exist!")
                            #cancel reservation
                            answers[qcode] = "expired"

                            message = process_answers(answers,json_data)
                            #print(message)
                            
                            table_reservation_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)
                            #raw_reservations['user_reservations'][username][subpage_title]

                            
                            
                            if (not find_inline_reservation(raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and not find_inline_reservation(pretreated_raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and table_reservation_line not in tmp_text):
                                #tmp_text+=f"\n*{table_reservation_line}\n{message}"
                                if topic_page in pages_to_save.keys():
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                                else:
                                    INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                                    pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                            #print(f"Potentially suspicious line: {reservation['reservation_line']}")
                            #print(f"*{reservation['reservation_line']}\n{message}")
                                        
                            #remove reservation from table if already there
                            section_title = qcode_dict[qcode][0]["section_title"]
                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                            rownum = qcode_dict[qcode][0]["rownum"]
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title])
                            #print(dictionarized_topics_tables[subpage_title])
                            dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname] = ""
                            rewrite_table = True
                            #print("rewrite table, remove")
                        elif hf.user_modified_page_since(page, user, reservation['date']):
                            #check if there's no conflicting reservation in another table by another participant
                            #can only happen if the topic is invoked in multiple tables
                            #no such case for arwiki
                            if len(qcode_dict[qcode]) > 1:
                                print("WARNING!!!!! ",qcode, qcode_dict[qcode])
                            
                            #approve reservation in-line
                            answers[qcode] = "accepted"
                            #save to user contribution dictionary
                            capitalized_user = hf.properly_capitalize(user)
                            if capitalized_user in all_participants_contributions.keys():
                                if qcode not in all_participants_contributions[capitalized_user]:
                                    all_participants_contributions[capitalized_user].append(qcode)
                                                    
                            else:
                                all_participants_contributions[capitalized_user] = [qcode]
                            #print(f"page {page.title()} was modified by user {user}!")
                            message = process_answers(answers,json_data)
                            #print(message)
                            
                            table_reservation_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)
                            if (not find_inline_reservation(raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and not find_inline_reservation(pretreated_raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and table_reservation_line not in tmp_text):
                                if topic_page in pages_to_save.keys():
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                                else:
                                    INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                                    pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"

                                
                                
                                    
                            #print(f"Potentially suspicious line: {reservation['reservation_line']}")
                            #print(f"*{reservation['reservation_line']}\n{message}")
                            
                        else:
                            #print(reservation['date'])
                            #print(user)
                            #print(list(page.revisions(reverse=True, starttime=datetime(2023, 4, 25, 0, 0), endtime=min(datetime.now(), datetime(2023, 6, 10, 11, 59)))))
                            #else cancel reservation, and remove reservation from table if already there
                            answers[qcode] = "expired"
                            #print("rownum: ",qcode_dict[qcode][0]["rownum"])
                            #print(f"page {page.title()} has not been modified by user {user}!")

                            message = process_answers(answers,json_data)
                            #print(message)
                            #INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                            table_reservation_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)

                            #must also check if there's no equivalent reservation in the reservation section
                            #invoke the raw_reservations of the user and compare
                            if (not find_inline_reservation(raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and not find_inline_reservation(pretreated_raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and table_reservation_line not in tmp_text):
                                #tmp_text+=f"\n*{table_reservation_line}\n{message}"
                                if topic_page in pages_to_save.keys():
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                                else:
                                    INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                                    pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                            #print(f"Potentially suspicious line: {reservation['reservation_line']}")
                            #print(f"*{reservation['reservation_line']}\n{message}")
                            #print(subpage_title)
                            #print(qcode_dict[qcode])
                            section_title = qcode_dict[qcode][0]["section_title"]
                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                            rownum = qcode_dict[qcode][0]["rownum"]
                            #print(dictionarized_topics_tables[subpage_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum])
                            
                            
                            
                            dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname] = ""
                            rewrite_table = True
                            #print("rewrite table, remove")
                    else:
                        qcode = reservation['reserved_code']
                        #print(qcode)
                        page = hf.get_wikipedia_page(qcode, lang)
                        if page is not None and hf.user_modified_page_since(page, user, reservation['date']):
                            #check if there's no conflicting reservation in another table by another participant
                            #can only happen if the topic is invoked in multiple tables
                            #no such case for arwiki
                            if len(qcode_dict[qcode]) > 1:
                                print("WARNING!!!!! ",qcode, qcode_dict[qcode])
                            
                            #approve reservation in-line
                            answers[qcode] = "accepted"
                            #save to user contribution dictionary
                            capitalized_user = hf.properly_capitalize(user)
                            if capitalized_user in all_participants_contributions.keys():
                                if qcode not in all_participants_contributions[capitalized_user]:
                                    all_participants_contributions[capitalized_user].append(qcode)
                                                    
                            else:
                                all_participants_contributions[capitalized_user] = [qcode]
                            #print(f"page {page.title()} was modified by user {user}!")
                            message = process_answers(answers,json_data)
                            #print(message)
                            
                            table_reservation_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)
                            if (not find_inline_reservation(raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and not find_inline_reservation(pretreated_raw_reservations['user_reservations'], reservation, user, subpage_title)
                                and table_reservation_line not in tmp_text):
                                if topic_page in pages_to_save.keys():
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                                else:
                                    INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                                    pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                                    pages_to_save[topic_page]["text"] +=f"\n*{table_reservation_line}\n{message}"
                                    
                if rewrite_table:
                    updated_table = hf.list_of_dicts_to_wikitext_table(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                    #print(updated_table)
                    #print(topics_tables[topic][section_title][subsection_title])
                    #tmp_text = tmp_text.replace(topics_tables[topic][section_title][subsection_title],updated_table)
                    if topic_page in pages_to_save.keys():
                        pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)
                    else:
                        INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                        pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                        pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)            
                            
                          
            if tmp_text != topic_page.text:
                #print("updating topics page")
                if topic_page in pages_to_save.keys():
                    pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)
                else:
                    INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                    pages_to_save[topic_page] = {"text":"", "save_message":INTABLE_RESERVATION_PROCESSING}
                    pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)
                #INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                #topic_page.text = tmp_text
                #topic_page.save(INTABLE_RESERVATION_PROCESSING)
                                       
                            
                            
            #make sure to check for conflicting reservations
            #print(topic_reservation['reservation'])
            #print(topic_reservation['reserved_topics'])
            """      
            else:
                #copy reservation to table line and add response
                pass
            """

    return notification_list, pages_to_save, all_participants_contributions



def process_untreated_raw_reservations(pretreated_raw_user_reservations
                                       , participants
                                       , json_data
                                       , notification_list):
    #print("pretreated_raw_reservations")
    jury = json_data['jury']
    organizers = json_data['organizers']
    bot = json_data['bot']
    for user, reservations in pretreated_raw_user_reservations.items():
        if is_not_valid_participant(user,participants,jury,organizers,bot):
            #print(user)
            #print(bot)
            subpage_title = list(reservations.keys())[0]
            #print(subpage_title)
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-8] not in notifications_page.text:
                notification_list.append(new_notification)

    return notification_list

def consolidate_pretreated_reservations(pretreated_raw_user_reservations):

    pretreated_user_reservations_by_subpage = {}
    for user, reservations in pretreated_raw_user_reservations.items():
        for subpage_title, topic_reservations in reservations.items():
            for reservation in topic_reservations:
                if subpage_title in pretreated_user_reservations_by_subpage.keys():
                    pretreated_user_reservations_by_subpage[subpage_title].append({'user':user
                                                                                  ,'qcodes': reservation['reserved_topics']
                                                                                  ,'date': reservation['date']
                                                                                  ,'reservation':reservation['reservation']
                                                                                  ,'next_line':reservation['next_line']
                                                                                  ,'ignore':False})

                else:
                    pretreated_user_reservations_by_subpage[subpage_title]=[{'user':user
                                                                            ,'qcodes': reservation['reserved_topics']
                                                                            ,'date': reservation['date']
                                                                            ,'reservation':reservation['reservation']
                                                                            ,'next_line':reservation['next_line']
                                                                            ,'ignore':False}]
    return pretreated_user_reservations_by_subpage

def update_reservation_tables_with_pretreated(pretreated_user_reservations_by_subpage
                                              ,participants
                                              ,qcode_dict
                                              ,json_data
                                              ,dictionarized_topics_tables
                                              ,topics_tables
                                              ,notification_list
                                              ,pages_to_save):
    #load strings
    site = pywikibot.Site(json_data["lang"],"wikipedia")
    approved_template = json_data['translations']['templates']['approved_template']
    rejected_template = json_data['translations']['templates']['rejected_template']
    jury = json_data['jury']
    organizers = json_data['organizers']
    bot = json_data['bot']
    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_male_namespace = json_data['translations']['namespaces']['user_male']
    user_female_namespace = json_data['translations']['namespaces']['user_female']
    user_template_name = json_data['translations']['templates']['user_template']
    #rewrite_table = False
    for subpage_title, reservations in pretreated_user_reservations_by_subpage.items():
        rewrite_table = False
        subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
        for reservation in reservations:
            user = reservation['user']
            
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            if is_not_valid_participant(user,participants,jury,organizers,bot):
                print(user)
                new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
                if new_notification[:-4] not in notifications_page.text:
                    notification_list.append(new_notification)
            else:
                
                print(subpage_title)
                #answers = {}
                #if subpage_title == "فن وموسيقى": #to observe changes on a particular page
                if True:
                    reserved_topics = reservation['qcodes']
                    next_line = reservation['next_line']
                    next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_male_namespace, user_template_name)

                    if next_usernames is None:
                        next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_female_namespace, user_template_name)
                    #print(username)
                    #print(next_username)
                                
                    if next_usernames is not None:
                        if len(next_usernames) == 1:
                            next_username = next_usernames[0]
                        elif next_usernames[-1] in jury or next_usernames[-1] in organizers:
                            next_username = next_usernames[-1]
                        else:
                            next_username = next_usernames[0]
                    if "{{"+approved_template+"}}" in next_line and (next_username in jury or next_username in organizers or next_username == bot):
                        #check if reservation should be added to the table
                        #raw_table_reservations["user_reservations"][user]
                        for qcode in reserved_topics:
                            topic = qcode_dict[qcode][0]["topic"]
                            section_title = qcode_dict[qcode][0]["section_title"]
                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                            rownum = qcode_dict[qcode][0]["rownum"]

                            print(qcode)
                            print(subpage_title)
                            print(section_title)
                            print(resrv_colname)
                            #print(qcode_dict[qcode])
                            #print(dictionarized_topics_tables[subpage_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum])
                            table_reservation_line = dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname]

                            if table_reservation_line == "":
                                #invoke get_table_reservation_line_from_inline_reservation
                                table_reservation_line = get_table_reservation_line_from_inline_reservation(reservation['reservation'],qcode,json_data,"underway")
                                dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname] = table_reservation_line
                                rewrite_table = True
                                print("rewrite table, add")
                            """
                            capitalized_user = hf.properly_capitalize(user)
                            if capitalized_user in all_participants_contributions.keys():
                                if qcode not in all_participants_contributions[capitalized_user]:
                                    all_participants_contributions[capitalized_user].append(qcode)
                                                    
                            else:
                                all_participants_contributions[capitalized_user] = [qcode]
                            """                
                        
                    elif "{{"+rejected_template+"}}" in next_line and (next_username in jury or next_username in organizers or next_username == bot):
                        #check if reservation should be removed from the table
                        for qcode in reserved_topics:
                            topic = qcode_dict[qcode][0]["topic"]
                            section_title = qcode_dict[qcode][0]["section_title"]
                            subsection_title = qcode_dict[qcode][0]["subsection_title"]
                            rownum = qcode_dict[qcode][0]["rownum"]
                            print(qcode)
                            print(subpage_title)
                            print(section_title)
                            print(resrv_colname)
                            #print(dictionarized_topics_tables[subpage_title])
                            
                            #print(dictionarized_topics_tables[subpage_title][section_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
                            #print(dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum])
                            table_reservation_line = dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname]

                            if table_reservation_line != "":
                                #invoke get_table_reservation_line_from_inline_reservation
                                dictionarized_topics_tables[subpage_title][section_title][subsection_title][rownum][resrv_colname] = ""
                                rewrite_table = True
                                print("rewrite table, remove")
            
        if rewrite_table:
            
            updated_table = hf.list_of_dicts_to_wikitext_table(dictionarized_topics_tables[subpage_title][section_title][subsection_title])
            print(updated_table)
            topic_page = pywikibot.Page(site,subpage_link)
            #print(topics_tables[topic][section_title][subsection_title])
            #tmp_text = tmp_text.replace(topics_tables[topic][section_title][subsection_title],updated_table)
            if topic_page in pages_to_save.keys():
                pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)
            else:
                INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                pages_to_save[topic_page] = {"text":topic_page.text, "save_message":INTABLE_RESERVATION_PROCESSING}
                pages_to_save[topic_page]["text"] = pages_to_save[topic_page]["text"].replace(topics_tables[subpage_title][section_title][subsection_title],updated_table)

    return notification_list, pages_to_save

def save_participants_pages(all_participants_contributions, json_data):
    root_participant_link = f'{json_data["pages"]["main_page"]}/{json_data["pages"]["participants_page"]}'

    month_names = json_data['months']

    
    participant_points = {}

    for participant, qcodes in all_participants_contributions.items():
        print(participant, hf.get_user_contributions_until(participant, site))
        
        wiki_table, total_points, total_articles, total_user_contributions, total_no_issues_articles = generate_wiki_table(lang, participant, qcodes, qcode_dict, site, json_data)

        participant_points[participant] = {"total_points":total_points
                                           , "total_articles":total_articles
                                           , "total_user_contributions":total_user_contributions
                                           , "total_no_issues_articles":total_no_issues_articles}

        last_update_date = datetime.utcnow().strftime(json_data['date_format'])

        last_update_date = re.sub(r'-(\d{2})-', lambda m: ' ' + month_names[int(m.group(1)) - 1] + ' ', last_update_date)

        last_update_date = last_update_date.replace(",",json_data["comma"])

        header_text_page_title = json_data["translations"]["points"]["header_text_page"]

        header_text_page = pywikibot.Page(site,header_text_page_title)

        header_text = header_text_page.text.replace("{user}",participant).replace("{total_points}",str(total_points)).replace("{last_update_date}",last_update_date)

        participant_page_title = f'{root_participant_link}/{participant}'

        participant_page = pywikibot.Page(site,participant_page_title)

        text = header_text+'\n\n'+wiki_table

        #print(text)

        #break

        if text != participant_page.text:
            participant_page.text = text
            save_message = json_data["SAVE_MESSAGES_DICT"]["UPDATE_PARTICIPANT_PAGE"]
            participant_page.save(save_message)

    return participant_points

def update_ranking_tables_non_ar(contributors_table, json_data):
    print(contributors_table)

    month_names = json_data['months']

    footer_text = json_data["translations"]["ranking"]["footer_text"]

    save_message = json_data["SAVE_MESSAGES_DICT"]["UPDATE_RANKING"]

    contributors_ranking_title = json_data["translations"]["ranking"]["ranking_title"]

    page_ranking = pywikibot.Page(site,contributors_ranking_title)

    last_update_date = datetime.utcnow().strftime(json_data['date_format'])

    last_update_date = re.sub(r'-(\d{2})-', lambda m: ' ' + month_names[int(m.group(1)) - 1] + ' ', last_update_date)

    last_update_date = last_update_date.replace(",",json_data["comma"])

    header_text_page_title = json_data["translations"]["ranking"]["header_text_page"]

    header_text_page = pywikibot.Page(site,header_text_page_title)

    page_type = contributors_ranking_title.split('/')[-1]

    header_text = header_text_page.text.replace("{page_type}",page_type).replace("{last_update_date}",last_update_date)

    text = f"{header_text}\n\n{contributors_table}\n{footer_text}"

    if page_ranking.text != text:

        page_ranking.text = text

        page_ranking.save(save_message)

def update_ranking_tables_ar(beginners_table, advanced_table, json_data):
    print(beginners_table)

    month_names = json_data['months']

    footer_text = json_data["translations"]["ranking"]["footer_text"]

    save_message = json_data["SAVE_MESSAGES_DICT"]["UPDATE_RANKING"]

    beginners_ranking_title = json_data["translations"]["ranking"]["beginners_ranking_title"]

    page_ranking_beg = pywikibot.Page(site,beginners_ranking_title)

    last_update_date = datetime.utcnow().strftime(json_data['date_format'])

    last_update_date = re.sub(r'-(\d{2})-', lambda m: ' ' + month_names[int(m.group(1)) - 1] + ' ', last_update_date)

    last_update_date = last_update_date.replace(",",json_data["comma"])

    header_text_page_title = json_data["translations"]["ranking"]["header_text_page"]

    header_text_page = pywikibot.Page(site,header_text_page_title)

    page_type = beginners_ranking_title.split('/')[-1]

    header_text = header_text_page.text.replace("{page_type}",page_type).replace("{last_update_date}",last_update_date)

    text = f"{header_text}\n\n{beginners_table}\n{footer_text}"

    if page_ranking_beg.text != text:

        page_ranking_beg.text = text

        page_ranking_beg.save(save_message)

    print(advanced_table)

    advanced_ranking_title = json_data["translations"]["ranking"]["advanced_ranking_title"]

    page_ranking_adv = pywikibot.Page(site,advanced_ranking_title)

    last_update_date = datetime.utcnow().strftime(json_data['date_format'])

    last_update_date = re.sub(r'-(\d{2})-', lambda m: ' ' + month_names[int(m.group(1)) - 1] + ' ', last_update_date)

    last_update_date = last_update_date.replace(",",json_data["comma"])

    header_text_page_title = json_data["translations"]["ranking"]["header_text_page"]

    header_text_page = pywikibot.Page(site,header_text_page_title)

    page_type = advanced_ranking_title.split('/')[-1]

    header_text = header_text_page.text.replace("{page_type}",page_type).replace("{last_update_date}",last_update_date)

    text = f"{header_text}\n\n{advanced_table}\n{footer_text}"

    if page_ranking_adv .text!= text:

        page_ranking_adv.text = text

        page_ranking_adv.save(save_message)
    

# Main section
if __name__ == "__main__":

    #set variables
    lang = ""
    while lang not in ["ar","ary"]:
        lang = input("Enter the language code: ")
    site = pywikibot.Site(lang,"wikipedia")
    json_page_title = f"Mediawiki:{lang}_translation.json"
    json_data = hf.read_json_file(pywikibot.Site(JSON_SITE_LANG[lang],"wikipedia"), json_page_title)

    notifications = json_data['notifications']
    #jury = json_data['jury']
    #organizers = json_data['organizers']
    #bot = json_data['bot']
    
    #unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    #user_male_namespace = json_data['translations']['namespaces']['user_male']
    #user_female_namespace = json_data['translations']['namespaces']['user_female']
    #user_template_name = json_data['translations']['templates']['user_template']

    resrv_colname = json_data['translations']['reservation_status']

    user_participating_full_template = json_data['translations']['templates']['user_participating_full_template']

    #morocco_contest_cat = json_data['translations']['categories']['MOROCCO_CONTEST_CAT']

    # Fetch the participant list   
    participants = hf.load_participants(site,json_data)

    print(participants)

    #fetch the topic tables raw with their wiki code
    topics_tables = load_topics_tables(site,json_data)
    #transform raw wikicode to a list of rows, each represented by a dictionary (overall same struct as topics_tables)
    #create a dictionary that contains the topics as keys, for easier access (instead of looping through the table structs
    #several times to find the same information
    dictionarized_topics_tables, qcode_dict = convert_topics_tables_to_dicts(topics_tables,json_data)

    """
    with open("qcode_dict.txt","w", encoding="utf-8") as qc:
        qc.write(str(qcode_dict))

    with open("topics_tables.txt","w", encoding="utf-8") as dt:
        topic = "رياضة"
        section_title = "لاعبو ولاعبات منتخب المغرب"
        subsection_title = "للتطوير"
        dt.write(str(topics_tables[topic][section_title][subsection_title]))
    """
    

    #print(len(qcode_dict.keys()))

    
    #print(dictionarized_topics_tables == topics_tables)
    '''
    topic = "فن وموسيقى"
    section_title = "فنانون وموسيقيون"
    subsection_title = "غير موجود"
    
    for i in range(len(dictionarized_topics_tables[topic][section_title][subsection_title])):
        qcode = hf.extract_qcodes(dictionarized_topics_tables[topic][section_title][subsection_title][i][json_data["translations"]["topic"]])[0]
        print(i, dictionarized_topics_tables[topic][section_title][subsection_title][i]["الموضوع"])
        print(qcode_dict[qcode][0]["rownum"],qcode)
        dictionarized_topics_tables[topic][section_title][subsection_title][i]['رقم المقالة'] = str(i+1)

    wikicode = hf.list_of_dicts_to_wikitext_table(dictionarized_topics_tables[topic][section_title][subsection_title])
    print(wikicode)
    '''
    #print(dictionarized_topics_tables[topic][section_title][subsection_title]) #[rownum]

    #print(type(topics_tables[topic][section_title][subsection_title][0]))
    #print(topics_tables[topic][section_title][subsection_title][0].keys())
    #print(topics_tables[topic][section_title][subsection_title])

    #print()
    
    
    #make sure no qcodes are repeated
    for qcode, content in qcode_dict.items():
        #print(qcode, len(content))
        if len(content)>1:
            print('qcodes: ',qcode, content)

    '''
    #"""
    #fetch the user reservations from the tables
    '''
    raw_table_reservations = get_user_reservations_from_table(dictionarized_topics_tables,json_data)

    #fetch inline reservations
    #dictionary key = user, value = list of qcodes of reserved topics
    raw_reservations, pretreated_raw_reservations, discarded_lines = process_raw_reservations(site,json_data)

    #run checks and add to notification list
    
    notification_list = []
    notifications_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['notifications_page']}"
    #print(notifications_page_title)
    notifications_page = pywikibot.Page(site,notifications_page_title)

    #rewrite_table = False

    pages_to_save = {}

    all_participants_contributions = {} #dictionary containing the qcodes each user has contributed to

    #process participants list
    print("Process participants")
    #notification_list = process_participants(participants, json_data, notification_list)

    #Process unprocessed inline reservations
    print("Process unprocessed inline reservations")
    
    notification_list, pages_to_save = process_unprocessed_inline_reservations(raw_reservations["user_reservations"]
                                                                            , participants
                                                                            , json_data
                                                                            , topics_tables
                                                                            , dictionarized_topics_tables
                                                                            , qcode_dict
                                                                            , notification_list
                                                                            , pages_to_save)

    #'''   
    

    #validate reservations in tables
    #model content: {"topic":topic,"section_title":section_title,"subsection_title":subsection_title,"rownum":i
                #,"reservation_line":table[i][resrv_colname],'date':date,'':'reserved_code':extract_qcodes(table[i]['topic'])}

    #print(raw_table_reservations["improper_reservations"])
    #'''
    print("raw_table_reservations")
    
    #'''

    print("Process table reservations")
    
    notification_list, pages_to_save, all_participants_contributions = process_raw_table_reservations(raw_table_reservations["user_reservations"]
                                                                                                   , participants
                                                                                                   , json_data
                                                                                                   , topics_tables
                                                                                                   , qcode_dict
                                                                                                   , dictionarized_topics_tables
                                                                                                   , notification_list
                                                                                                   , pages_to_save
                                                                                                   , all_participants_contributions)

    #'''                               
    #pretreated_reservations

    """
    Consolidate pretreated reservations, and convert format with subpage titles as main keys
    """
    print("pretreated_raw_reservations")
    notification_list = process_untreated_raw_reservations(pretreated_raw_reservations["user_reservations"], participants, json_data, notification_list)
    
    
    #'''
    
    print("Consolidate pretreated reservations, and convert format with subpage titles as main keys")
    pretreated_user_reservations_by_subpage = consolidate_pretreated_reservations(pretreated_raw_reservations["user_reservations"])

    
                                        
    '''
    #subpage_title = "تاريخ"
    #print(pretreated_user_reservations_by_subpage[subpage_title])
    """
    Archive old rejected reservations
    
    """
    #print("Archive old rejected reservations")

    #TODO later, maybe, way easier to do by hand
    
    '''

    print("update reservation tables from pretreated reservation lines")

    
    notification_list, pages_to_save = update_reservation_tables_with_pretreated(pretreated_user_reservations_by_subpage
                                                                              ,participants
                                                                              ,qcode_dict
                                                                              ,json_data
                                                                              ,dictionarized_topics_tables
                                                                              ,topics_tables
                                                                              ,notification_list
                                                                              ,pages_to_save)
               
        
    #'''
    """
    Advanced checks and evaluation
    """
    
    """
    Saving reservation pages
    
    """
    
    
    print("saving pages, count", len(pages_to_save))
    for page, save_elements in pages_to_save.items():
        print("saving",page.title())
        if page.text != save_elements["text"]:
            page.text = save_elements["text"]
            #print(page.text)
            page.save(save_elements["save_message"])
    
    '''

    """
    Saving notifications page
    
    """
    '''
    
    if len(notification_list)>0:
        notifications ='*'+'\n*'.join(notification_list)

        #print(notifications)

        write_to_notification_page(notifications,notifications_page,json_data)
    #"""
    """
    #save content of tables for debugging
    output = topics_tables
    
    with open("output.txt","w",encoding="utf-8") as out:
        out.write(str(output))
    """
    #write_notifications(site,notification_list,notification_page_title=f"{json_data['notification_page']}",save_message=f"{json_data['SAVE_MESSAGES_DICT']['save_to_notification_page']}")
    
    # Process the topic reservations
    
    # Handle reservations expiring after 24 hours
    #handle_expired_reservations()
    #'''

    
    print("All contributions")

    
    
    #print(all_participants_contributions)
    #print(len(all_participants_contributions.keys()))

    
    with open("all_participants_contributions.txt",'w', encoding="utf-8") as apc:
        apc.write(str(all_participants_contributions))
    """
    
    #easier for debugging or restarting this section
    
    with open("all_participants_contributions.txt",'r', encoding="utf-8") as apc:
        all_participants_contributions = ast.literal_eval(apc.read())
    #"""

    
    print("saving contribution pages for each participant")

    participant_points = save_participants_pages(all_participants_contributions, json_data)
    
    #print(participant_points)
    
    with open("participant_points.txt",'w', encoding="utf-8") as pp:
        pp.write(str(participant_points))

    """
    
    with open("participant_points.txt",'r', encoding="utf-8") as pp:
        participant_points = ast.literal_eval(pp.read())
    #"""

    #ranking tables
    #"""

    root_participant_link = f'{json_data["pages"]["main_page"]}/{json_data["pages"]["participants_page"]}'
    if lang == "ar":
        beginners_table, advanced_table = separate_and_rank_users_ar(participant_points, root_participant_link)

        update_ranking_tables_ar(beginners_table, advanced_table, json_data)

    else:
        contributors_table = separate_and_rank_users_non_ar(participant_points, root_participant_link)

        update_ranking_tables_non_ar(contributors_table, json_data)
    

    #"""

    #writing full contributions table

    

