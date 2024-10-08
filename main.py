import re
import sys
from datetime import datetime, timedelta
import mysql.connector
import jinja2

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os
from dotenv import load_dotenv
from loguru import logger

# set the start hour for the report.  6 = six am yesterday to six am today
start_hour = 6

load_dotenv()

logger.debug("Running")

email_config = {
    'server': 'smtp01.stackpole.ca',
    'from': 'tyler.careless@johnsonelectric.com',
    'to': [
        'tyler.careless@johnsonelectric.com',
    ],
    'subject': 'Press Changeovers'
}

db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': 'prodrptdb',
    # 'raise_on_warnings': True
}

def completed_changeovers(start,end):
    results = []
    with mysql.connector.connect(**db_config) as cnx:
        cursor = cnx.cursor()

        query = ("SELECT * FROM pr_downtime1 "
                "WHERE priority = -2 "
                "AND ( completedtime BETWEEN %s AND %s)")

        cursor.execute(query,(start, end))

        for row in cursor:
            record = {
                'machine': row[0],
                'problem': row[1],
                'comments': row[8],
                'updatedtime': row[10],
                'completedtime': row[7],
                'changeovertime': row[15],
                'setupdelta': row[15]-row[10],
                'dialindelta': row[7]-row[15],
            } 

            results.append(record)
            # print(results)
    return results

def pending_changeovers(start,end):
    results = []
    with mysql.connector.connect(**db_config) as cnx:
        cursor = cnx.cursor()

        query  = f'SELECT * FROM pr_downtime1 '
        query += f'WHERE priority = -1;'

        cursor.execute(query)

        for row in cursor:
            print(row)
            record = {
                'machine': row[0],
                'problem': row[1],
                'called4helptime': row[2],
            } 

            results.append(record)
            # print(results)
    return results


def shift_times(date, date_offset=0):
    # end_date is today at {start_hour}
    end_date = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    # adjust end_date by date_offset days
    end_date = end_date - timedelta(days=date_offset)
    # start_date is the day before at {start_hour}
    start_date = end_date - timedelta(hours=24)
    end_date = end_date - timedelta(seconds=1)
    return start_date, end_date


def get_report_data(start, end):

    pending_list = pending_changeovers(start, end)
    completed_list = completed_changeovers(start, end)
    data = {
        'start': start,
        'end': end,
        'completed_list': completed_list,
        'pending_list': pending_list,
    }
    # print(data)
    return data



def report_html(start, end):
    data = get_report_data(start, end)
    # print(data)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=''),
        extensions=["jinja2_humanize_extension.HumanizeExtension"]
        )
    template = env.get_template('template.html')
    return template.render(data=data)

@logger.catch
def main():
    offset = 0 if len(sys.argv) == 1 else int(sys.argv[1])
    start_time, end_time = shift_times(datetime.now(), offset)
    report = report_html(start_time, end_time)
    message = MIMEMultipart("alternative")
    message["Subject"] = email_config['subject']
    message["From"] = email_config['from']
    message["To"] = ", ".join(email_config['to'])
    msg_body = MIMEText(report, "html")
    message.attach(msg_body)
    server = smtplib.SMTP(email_config['server'])
    server.sendmail(email_config['from'], email_config['to'], message.as_string())
    server.quit()

if __name__ == '__main__':
    main()
