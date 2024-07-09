import io
import calendar
from datetime import datetime, timedelta
import pytz
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(page_title="<name>", page_icon="🏢", layout="wide", menu_items=None)

timezone = pytz.timezone("Europe/Belgrade")
con = MongoClient("localhost", 27017)
accs = con.main.accounts
jobs = con.main.jobs
tasks = con.main.tasks
c = EncryptedCookieManager(password='<password>')

alltasks = tasks.find_one()
alltasks_inv = {}
if alltasks is not None:
    del alltasks["_id"]

    for i, j in list(alltasks.items()):
        alltasks_inv[j] = i

if not c.ready():
    st.stop()

odjava = st.empty()
tmp = st.empty()
tmp2 = st.empty()
try:
    a = c['logged']
except Exception:
    c['logged'] = 'false'


def date_decode(date):
    return datetime.strptime(date, "%a %b %d %H:%M:%S %Y")

def date_encode(date):
    return date.strftime("%a %b %d %H:%M:%S %Y")

def remove_accs(stuff):
    global accs
    for i in stuff:
        if i[0] == True:
            accs.delete_one({"name": i[1]})

def remove_proj(stuff):
    global jobs
    for i in stuff:
        if i[0] == True:
            jobs.delete_one({"name": i[1]})

def remove_task(stuff):
    global jobs
    for i in stuff:
        if i[0] == True:
            update = jobs.find_one({"name": i[3]})[i[2]]
            update.remove(i[1])                
            jobs.update_one({"name": i[3]}, {"$set": {i[2]: update}})
@st.experimental_dialog("Are you sure?")
def remove():
    if st.button("Yes", type="primary"):
        return True
    if st.button("No"):
        return False

def run():
    global accs, jobs, odjava, c
    workers = [i['name'] for i in accs.find({"role": {"$ne": "admin"}})]
    working = False
    tasks = []
    c.save()
    if odjava.container().button('Log out'):
        del c['user']
        del c['r']
        del c['name']
        del c['logged']
        odjava.empty()
        st.rerun()

    with st.container():
        izv, people, active_projects, stats, create_jobs, create_accs, remove = st.tabs(["Report", "Workers", "Projects", "Stats", "New project", "New worker", "Remove"])

        with izv:
            data = {"Worker": [], "Project": [], "Task": [], "Start": [], "End": []}
            datum = st.date_input("Choose a date", value="today")
            for j in jobs.find():
                for i in list(alltasks.values()):
                    for k in j[i]:
                        date = date_decode(k['time'][0][1])
                        datep = date_decode(k['time'][0][0])


                        if date.day == datum.day and date.month == datum.month and date.year == datum.year:
                            data["Start"].append(datep)
                            data['Worker'].append(k['person'])
                            data["Project"].append(j['name'])
                            data["Task"].append(alltasks_inv[i])
                            data["End"].append(date)

            st.subheader("Report")
            st.table(data)

        with people:
            w = st.selectbox("Choose a worker", workers, key=1)
            data_tabela = pd.DataFrame({"Project": ["" for _ in range(5)], "Task": ["" for _ in range(5)], "Start": [datetime(2024, 1, 1, 0, 0) for _ in range(5)], "End": [datetime(2024, 1, 1, 0, 0) for _ in range(5)]})   
            tabela = st.data_editor(data_tabela, column_config={"Project": st.column_config.SelectboxColumn("Project", options=[i['name'] for i in jobs.find()]), "Task": st.column_config.SelectboxColumn("Task", options=list(alltasks.keys())), "Start": st.column_config.DatetimeColumn("Start", format="ddd MMM DD HH:mm:ss YYYY"), "End": st.column_config.DatetimeColumn("End", format="ddd MMM DD HH:mm:ss YYYY")}, use_container_width=True, hide_index=True)
            if st.button("Save"):
                try:
                    test = st.session_state.tabela
                except Exception:
                    st.session_state.tabela = {}
                if st.session_state.tabela != tabela.to_dict():
                    for i in range(5):
                        if tabela["Project"][i] != None and tabela["Project"][i] != "" and tabela["Task"][i] != None and tabela["Task"][i] != "":
                            update_list = jobs.find_one({"name": tabela['Project'][i]})[alltasks[tabela["Task"][i]]]
                            update_list.append({"person": w, "time": [(date_encode(tabela["Pocetak"][i]), date_encode(tabela["Task"][i]))]})
                            jobs.update_one({"name": tabela["Project"][i]}, {"$set": {alltasks[tabela["Task"][i]]: update_list}})
                    st.success("Successfully saved")
                    st.session_state.tabela = tabela.to_dict()

        with active_projects:
            active_proj = st.selectbox("Choose a project", [x['name'] for x in jobs.find()])
            st.divider()
            jobs_list = [0 for _ in range(len(list(alltasks.values())))]
            with st.expander("Time by worker"):
                st.write(" ")
                for i in workers:
                    v = 0
                    nv = 0
                    for index, k in enumerate(list(alltasks.values())):
                        sv = 0
                        for l in jobs.find_one({"name": active_proj})[k]:
                            if l['person'] == i:
                                start = l['time'][0][0]
                                end = l['time'][0][1]
                                v+=round((date_decode(end) - date_decode(start)).seconds/3600, 2)
                                sv+=round((date_decode(end) - date_decode(start)).seconds/3600, 2)
                        jobs_list[index]+=round(sv, 2)*accs.find_one({"name": i})['sat']
                    if v > 0:
                        st.markdown(f"""{i}   
                                        Hours: {round(v, 2)} = {round(v, 2)*accs.find_one({"name": i})['sat']} din""")

            st.divider()
            with st.expander("Time by task"):
                v_uk = 0
                for index, k in enumerate(list(alltasks.values())+['ukupno']):
                    v = 0
                    if k != 'ukupno':
                        for l in jobs.find_one({"name": active_proj})[k]:
                            start = l['time'][0][0]
                            end = l['time'][0][1]
                            v+=round((date_decode(end) - date_decode(start)).seconds/3600, 2)
                        v_uk += v
                    try:
                        test_zad = alltasks_inv[k]
                    except KeyError:
                        st.write(f"Total - {round(v_uk, 2)}h = {round(sum(jobs_list), 2)} din")
                    else:
                        st.write(f"{alltasks_inv[k]} - {round(v, 2)}h = {round(jobs_list[index], 2)} din")
                    st.divider()
            st.divider()             


        with stats:
            person = st.selectbox("Choose a worker", workers)
            tasks = []
            times = []
            data = {'Work hours':[], 'Comment': []}
            data1 = {'Work hours': [], 'Comment': []}
            month = datetime.now().astimezone(timezone).month
            if month == 1:
                month1 = 12
            else:
                month1 = month - 1
            
            if month1 == 12:
                year1 = datetime.now().astimezone(timezone).year - 1
            else:
                year1 = datetime.now().astimezone(timezone).year
            year = datetime.now().astimezone(timezone).year
            index = [x for x in range(1, calendar.monthrange(year, month)[1]+1)] + ["Total"]
            index1 = [x for x in range(1, calendar.monthrange(year1, month1)[1]+1)] + ["Total"]
            data["Comment"] = [" " for _ in range(len(index))]
            data1["Comment"] = [" " for _ in range(len(index1))]
            if len([0 for x in accs.find()]) == 1:
                pass
            else:
                for i in jobs.find():
                    for j in list(alltasks.values()):
                        for k in i[j]:
                            if k['person'] == person:
                                times.append(k['time'][0])

                for i in index[:-1]:
                    s = 0
                    for j in times:
                        if i == date_decode(j[1]).day and month == date_decode(j[1]).month and year == date_decode(j[1]).year:
                            r = date_decode(j[1]) - date_decode(j[0])
                            try:
                                s+=(r.seconds/3600)
                            except Exception:
                                pass

                    data["Work hours"].append(round(s, 2))
                
                for i in index1[:-1]:
                    s = 0
                    for j in times:
                        if i == date_decode(j[1]).day and month1 == date_decode(j[1]).month and year1 == date_decode(j[1]).year:
                            r = date_decode(j[1]) - date_decode(j[0])
                            try:
                                s+=(r.seconds/3600)
                            except Exception:
                                pass

                    data1["Work hours"].append(round(s, 2))

                data["Work hours"].append(round(sum(data["Work hours"]), 2))
                data1["Work hours"].append(round(sum(data1["Work hours"]), 2))
                df = pd.DataFrame(data=data, index=index)
                df1 = pd.DataFrame(data=data1, index=index1)

                try:
                    old_df = pd.read_excel(f"data/{person}_{month}_{year}.xlsx")
                    test = old_df.to_dict()["Comment"]
                except Exception:
                    df.to_excel(f"data/{person}_{month}_{year}.xlsx")
                else:
                    comentar = list(old_df.to_dict()["Comment"].values())
                    data["Comment"] = comentar
                    df = pd.DataFrame(data=data, index=index)
                    df.to_excel(f"data/{person}_{month}_{year}.xlsx")
                

                buffer = io.BytesIO()
                buffer1 = io.BytesIO()

                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Sheet1")


                with pd.ExcelWriter(buffer1, engine="xlsxwriter") as writer:
                    df1.to_excel(writer, sheet_name="Sheet1")

                st.download_button("Worksheet of previous month", data=buffer1, mime="application/vnd.ms-excel", file_name=f"{person}_{month1}_{year1}.xlsx")
                st.download_button("Worksheet of current month", data=buffer, mime="application/vnd.ms-excel", file_name=f"{person}_{month}_{year}.xlsx")
                
                with st.expander("Add a comment"):
                    with st.form("change_of_worksheet"):
                        st.subheader(f"{month}_{year}")
                        data["Index"] = index
                        u_worksheet = st.data_editor(data, disabled=["Index", "Work hours"], column_order=["Index", "Work hours", "Comment"], use_container_width=True)
                        if st.form_submit_button("Apply"):
                            del u_worksheet["Index"]
                            df = pd.DataFrame(data=u_worksheet, index=index)
                            df.to_excel(f"data/{person}_{month}_{year}.xlsx")

                for i in jobs.find():
                    if accs.find_one({"name": person}) is not None:
                        task_list = []
                        for j in list(alltasks.items()):
                            for k in i[j[1]]:
                                if k['person'] == person:
                                    task_list.append((k, j[0]))
                        tasks.append((i['name'], task_list))
                for a, d in tasks:
                    with st.expander(a):
                        for b, c in d:
                            i = b['time'][0]
                            st.write(f"{i[0]} - {i[1]} ({date_decode(i[1]) - date_decode(i[0])})")
                            st.divider()

        with create_jobs:
            name = st.text_input("Project name")
            if st.button("Create a project") and name and jobs.find_one({"name": name}) is None:
                new_dict = {"name": name}
                for i in list(alltasks.values()):
                    new_dict[i] = []
                jobs.insert_one(new_dict)
                st.success("New project has been made")

        with create_accs:
            tmp = st.empty().container()
            with tmp.form("create_accs"):
                user_name = st.text_input("Full name")
                user_role = st.selectbox("Choose a role", ['administrator', "worker"])
                user_sat = st.number_input("Hourly rate")
                if st.form_submit_button("Create a new worker") and user_name and user_role and user_sat:
                    if user_role == "administrator":
                        accs.insert_one({"name": user_name, "role": "admin", "sat": user_sat})
                    else:
                        accs.insert_one({"name": user_name, "role": "worker", "sat": user_sat})
                    st.success("Account has been made")

        with remove:
            tmp2 = st.empty()
            tmp3 = st.empty()
            with tmp2.container():
                remove_select = st.selectbox("What do you want to remove?", ["Accounts", "Projects", "Tasks"])
                stuff = []
                if remove_select == "Accounts":
                    for i in accs.find({"role": {"$ne": "admin"}}):
                        stuff.append((st.checkbox(i['name']), i['name']))
                    if st.button("Remove"):
                        if remove():
                            remove_task(stuff)
                
                if remove_select == "Projects":
                    for i in jobs.find():
                        stuff.append((st.checkbox(i['name']), i['name']))
                    if st.button("Remove"):
                        if remove():
                            remove_proj(stuff)

                if remove_select == "Tasks":
                    project = st.selectbox("Choose a project", [x['name'] for x in jobs.find()])
                    project_object = jobs.find_one({"name": project})
                    for i in list(alltasks.values()):
                        for index, j in enumerate(project_object[i]):
                            stuff.append((st.checkbox(f"{j['person']} - {project} - {alltasks_inv[i]} - {j['time'][0][0]} - {j['time'][0][1]}", key=str(index)+str(j)+i), j, i, project))
                    if st.button("Remove"):
                        if remove():
                            remove_task(stuff)

if __name__ == "__main__":
    if c['logged'] == 'false':
        with tmp.form("log"):
            user = st.text_input("Username")
            if st.form_submit_button("Login"):
                accs = con.main.accounts
                tmp_acc = accs.find_one({"user": user})
                if tmp_acc['user']  == user and tmp_acc['role'] == "admin":
                    tmp.empty()
                    c['logged'] = 'true'
                    c['user'] = user
                    c['name'] = accs.find_one({"user": user})['name']
                    c['r'] = accs.find_one({"user": user})['role']
                else:
                    st.error("Wrong username")
    if c['logged'] == 'true':
        run()

