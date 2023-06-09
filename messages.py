messages = {
    'start_message':
        'Этот бот будет уведомлять вас о новых тикетах в <a href="http://support.srv/jira"><b><u>support.srv</u></b></a>, обновлениях статусов и комментариях.\nПройдите авторизацию для продолжения...',
    'auth_message':
        'Отправте боту ваш <u>персональный токен авторизации</u> из <b>support.srv</b>.\nДля получения токена необходимо:\n\n<i>В верхнем правом углу вашего <a href="http://support.srv/jira">аккаутна</a> перейти во вкладку</i> <b>Профиль</b>\n\n<i>В левой панели выберите вкладку</i> <b>Персональные токены доступа</b> <i>,далее кнопка</i> <b>Создать токен</b>\n\n<i>Придумайте имя и уберите галочку в чек-боксе <u>Автоматическое окончание срока действия</u></i>',
    'auth_message_exist':
        'Ваш токен авторизации <a href="http://support.srv/jira"><b><u>support.srv</u></b></a> уже присутствует в боте. В случае смены токена удалите свои данные  (/del_stop)  и пройдите авторизацию заново (/start)',
    'auth_success_message':
        'Теперь вы будете получать уведомления от бота',
    'auth_fall_message':
        'Аутентификация не была пройдена, проверьте корректность токена и повторите попытку.\n\nЕсли вы уверены в корректности отправленного токена, вероятно бот испытывает некоторые проблемы с подключением к серверу, повторите попытку позже...',
    'del_yourself_message_true':
        'Все ваши данные были удалены, бот больше не будет отправлять вам уведомления...'
    }

def generate_notification_mesage(data):
    data_type_notification = data['type_notification']
    permalink = data['details']['permalink']
    ticket_key = data['details']["ticket_key"]
    summary = data['details']["summary"]
    priority = data['details']["priority"]
    status = data['details']["status"]
    creator_displayname = data['details']["creator_displayname"]
    assignee_displayname = data['details']["assignee_displayname"]
    comments = data['details']["comments"]

    if data_type_notification == 'new_issue':
        header_text = f'<b>Добавлено новое <a href="{permalink}">задание</a>:</b>\n'
    elif data_type_notification == 'update_status':
        header_text = f'<b>Обновлён статус <a href="{permalink}">задания</a>:</b>\n'
    elif data_type_notification == 'client_update_status':
        header_text = f'<b>Cтатус <a href="{permalink}"> вашего задания</a> обновлён:</b>\n'
    elif data_type_notification == 'new_comment':
        header_text = f'<b><i>{comments["dilayName"]}</i> добавил(а) новый комментарий <a href="{permalink}">в задании</a>:</b>\n'
    elif data_type_notification == 'client_new_comment':
        header_text = f'<b><i>{comments["dilayName"]}</i> добавил(а) новый комментарий в <a href="{permalink}">вашем задании</a>:</b>\n'
    else:
        header_text = "Ошибка формирования ответа"

    text = f"""{header_text}
    Номер задания:  <i>{ticket_key}</i>
    Автор:  <i>{creator_displayname}</i>
    Исполнитель:  <i>{assignee_displayname}</i>
    Приоритет:  <i>{priority}</i>
    Статус:  <i>{status}</i>
    Краткое описание:  <i>{summary}</i>
    """

    if data_type_notification in ('new_comment', 'client_new_comment'):
        comment_body = comments['body']
        comment_body = comment_body.strip('\n\n')
        if comment_body.endswith('thumbnail!'):
            comment_body = '*Прикреплено изображение*'
        text = text + f"Комментарий: <i>{comment_body}</i>"

    return text








