from jira import JIRA
import ast
from messages import generate_notification_mesage
from config import Config, load_config


config: Config = load_config()
SERVER: str = config.server_url.url


def get_username_from_jira(token: str):
    try:
        j = JIRA(server=SERVER, token_auth=token)
        myself = j.myself()
        r = (myself["name"], myself["displayName"])
        return r
    except Exception:
        return 0


def get_issues_from_jira(token: str):
    issues: dict = {}  # --> {issue_key:{details}}
    j = JIRA(server=SERVER, token_auth=token)
    projects = j.projects()
    for project in projects:
        issues_proj = j.search_issues(f'project = {project}', maxResults=100, expand='changelog')
        for issue_iter in issues_proj:
            issue = j.issue(issue_iter)

            try:
                assignee = issue.raw['fields']['assignee']['name']
                assignee_displayname = issue.raw['fields']['assignee']['displayName']
            except TypeError:
                assignee = 'Не выбран'
                assignee_displayname = 'Не выбран'
            comments = issue.raw['fields']['comment']['comments']
            comments = [{"author": c['author']['name'], 'dilayName': c['author']['displayName'], 'body': c['body']} for c in comments]
            details = {
                    'permalink': issue.permalink(),
                    'ticket_key': issue.key,
                    'summary': issue.raw['fields']["summary"],
                    'priority': issue.raw['fields']["priority"]['name'],
                    'status': issue.fields.status.name,
                    'creator': issue.raw['fields']['creator']['name'],
                    'creator_displayname': issue.raw['fields']['creator']['displayName'],
                    'assignee': assignee,  # исполнитель, несли нету -> None
                    'assignee_displayname': assignee_displayname,
                    'comment_total': issue.raw['fields']['comment']['total'],  # это количество комментов
                    'comments': comments
                    }
            issues[issue.key] = details

    return issues


def create_list_of_obj_for_output_bot(data_base):
    """ Функция генерирует список словарей.
        Словари содержат информацию об обновлениях и используются функцией-планировщиком
    """
    messages_pool = []
    from_db_list = data_base.get_all_data()

    for db_i in range(len(from_db_list)):  # data base index

        from_db_iter_tuple = from_db_list[db_i]
        update_user_data = get_issues_from_jira(from_db_iter_tuple[1])  # from_db_iter_tuple[1] - это токен
        if not bool(from_db_iter_tuple[2]):  # !!!!
            continue
        from_db_user_data = ast.literal_eval(from_db_iter_tuple[2])

        keys_from_db_user_data = list(from_db_user_data.keys())
        keys_update_user_data = list(update_user_data.keys())
        new_issues_keys = set(keys_update_user_data).difference(set(keys_from_db_user_data))

        #  Новые тикеты
        for k in new_issues_keys:  # k - ключ нового тикета
            try:
                new_issue_obj = filter_new_issue_attachement(user_id=from_db_iter_tuple[0],
                                                             user_name=from_db_iter_tuple[3],
                                                             issue_details=update_user_data[k])
                if new_issue_obj:
                    messages_pool.append(new_issue_obj)
                else:
                    continue
            except KeyError:
                continue

        #  Обновления существующих тикетов
        for k in keys_from_db_user_data:
            try:
                # Обновления статусов
                update_status_issue_obj = filter_update_status_attachement(user_id=from_db_iter_tuple[0],
                                                                           user_name=from_db_iter_tuple[3],
                                                                           details_upd=update_user_data[k],
                                                                           details_db=from_db_user_data[k],
                                                                           data_base=data_base,
                                                                           messages_pool=messages_pool)
                if update_status_issue_obj:
                    for elem in update_status_issue_obj:
                        messages_pool.append(elem)

                # Новые комменты
                new_comments_issue_obj = filter_new_comments_attachement(user_id=from_db_iter_tuple[0],
                                                                         user_name=from_db_iter_tuple[3],
                                                                         details_upd=update_user_data[k],
                                                                         details_db=from_db_user_data[k],
                                                                         data_base=data_base,
                                                                         messages_pool=messages_pool)
                if new_comments_issue_obj:
                    for elem in new_comments_issue_obj:
                        messages_pool.append(elem)
            except KeyError:
                continue

        data_base.update_user_data(user_id=int(from_db_iter_tuple[0]), user_data=update_user_data)

    return messages_pool


def filter_new_issue_attachement(user_id, user_name, issue_details):

    data = {
            'myself_name': user_name,
            'type_notification': 'new_issue',
            'details': issue_details
            }

    if issue_details['assignee'] == 'Не выбран' and issue_details['creator'] != user_name:
        return {'user_id': user_id, 'message': generate_notification_mesage(data)}

    elif issue_details['assignee'] == user_name:
        return {'user_id': user_id, 'message': generate_notification_mesage(data)}

    else:
        return None


def filter_update_status_attachement(user_id, user_name, details_upd, details_db, data_base, messages_pool):
    """
    1.если происходит обновление статуса и нет исполнителя - оповещать всех + заказчика
    2.если происходит обновление статуса и есть исполнитель - оповещать только заказчика
    UDP - подразумевается, что во втором случае статус меняет исполнитель, и оповещений получать он не должен
    """
    result = []
    data = {
        'myself_name': user_name,
        'details': details_upd
    }
    # изменения в статусе
    if details_upd['status'] != details_db['status']:

        # ##block: Client
        client_id = data_base.get_user_id(user_name=details_upd['creator'])
        if client_id:
            data['type_notification'] = 'client_update_status'
            client_message = {'user_id': client_id, 'message': generate_notification_mesage(data)}
            #  проверяем, есть ли клиетская мессага в пуле мессаг
            if (client_message not in messages_pool) and (client_message not in result):
                result.append(client_message)
        # ##END block: Client

        # ##block: Assignee
        if details_upd['assignee'] == 'Не выбран':
            data['type_notification'] = 'update_status'
            cur_user_message = {'user_id': user_id, 'message': generate_notification_mesage(data)}
            if (cur_user_message not in messages_pool) and (cur_user_message not in result):
                result.append(cur_user_message)
        # ##END block: Assignee

        #  Дополнительное условие. Оповещение всех (кроме клиентов и исполнителя если он задан)
        elif details_upd['status'] == 'Решен':
            if details_upd['assignee'] != user_name:
                data['type_notification'] = 'update_status'
                cur2_user_message = {'user_id': user_id, 'message': generate_notification_mesage(data)}
                if (cur2_user_message not in messages_pool) and (cur2_user_message not in result):
                    result.append(cur2_user_message)


        if bool(result):
            return result
        else:
            return None


def filter_new_comments_attachement(user_id, user_name, details_upd, details_db, data_base, messages_pool):
    result = []
    data = {
        'myself_name': user_name,
        'details': details_upd}

    if details_upd['comment_total'] != details_db['comment_total']:
        new_comment = details_upd['comments'][int(details_upd['comment_total']) - 1]  # Индекс последнего коммента в списке
        data['details']['comments'] = new_comment

        # ##block: Client

        #  Если автор коммента не клиент - оповещение клиенту
        if new_comment['author'] != details_upd['creator']:
            client_id = data_base.get_user_id(user_name=details_upd['creator'])
            if client_id:
                data['type_notification'] = 'client_new_comment'
                client_message = {'user_id': client_id, 'message': generate_notification_mesage(data)}
                #  проверяем, есть ли клиетская мессага в пуле мессаг
                if client_message not in messages_pool:
                    result.append(client_message)
        # ##END block: Client

        """
        Если исполнитель не задан - оповещать всех, кроме автора коммента
        Если исполнитель задан и он не автор коммента  - оповестить только исполнителя
        """
        # ##block: Assignee
        if details_upd['assignee'] == 'Не выбран' and new_comment['author'] != user_name:
            data['type_notification'] = 'new_comment'
            cur_user_message = {'user_id': user_id, 'message': generate_notification_mesage(data)}
            result.append(cur_user_message)
        elif details_upd['assignee'] == user_name and new_comment['author'] != user_name:
            data['type_notification'] = 'new_comment'
            cur_user_message = {'user_id': user_id, 'message': generate_notification_mesage(data)}
            result.append(cur_user_message)
        # ##END block: Assignee
    if bool(result):
        return result
    else:
        return None
