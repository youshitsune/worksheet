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
c = EncryptedCookieManager(password='<password>')
alltasks = {"Nabavka": "n", "Mašinska priprema": "s", "Zavarivanje": "v", "Farbanje": "f", "Montiranje": "m", "Istovar materijala": "im", "Prevoz materijala": "pm", "Utovar": 'u', "Prevoz": "p", "Demontaža": "dm", "Uzimanje mera": "um", "Mašinska obrada": "mo", "Ostalo": "o"}
alltasks_inv = {"n": "Nabavka", "s": "Mašinska priprema", "v": "Zavarivanje", "f": "Farbanje", "m": "Montiranje", "im": "Istovar materijala", "pm": "Prevoz materijala", "u": "Utovar", "p": "Prevoz", "dm": "Demontaža", "um": "Uzimanje mera", "mo": "Mašinska obrada", "o": "Ostalo"}

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

def run():
    global accs, jobs, odjava, c
    workers = [i['name'] for i in accs.find({"role": {"$ne": "admin"}})]
    working = False
    tasks = []
    c.save()
    if odjava.container().button('Odjavi se'):
        del c['user']
        del c['r']
        del c['name']
        del c['logged']
        odjava.empty()
        st.rerun()

    with st.container():
        izv, people, active_projects, stats, create_jobs, create_accs, remove = st.tabs(["Izveštaj","Radnici","Projekti", "Statistika", "Novi projekat", "Novi nalog", "Ukloni"])

        with izv:
            data = {"Radnik": [], "Projekat": [], "Zadatak": [], "Pocetak": [], "Kraj": []}
            datum = st.date_input("Izaberi datum", value="today")
            for j in jobs.find():
                for i in list(alltasks.values()):
                    for k in j[i]:
                        date = date_decode(k['time'][0][1])
                        datep = date_decode(k['time'][0][0])


                        if date.day == datum.day and date.month == datum.month and date.year == datum.year:
                            data["Pocetak"].append(datep)
                            data['Radnik'].append(k['person'])
                            data["Projekat"].append(j['name'])
                            data["Zadatak"].append(alltasks_inv[i])
                            data["Kraj"].append(date)

            st.subheader("Izveštaj")
            st.table(data)

        with people:
            w = st.selectbox("Izaberi radnika", workers, key=1)
            data_tabela = pd.DataFrame({"Projekat": ["" for _ in range(5)], "Zadatak": ["" for _ in range(5)], "Pocetak": [datetime(2024, 1, 1, 0, 0) for _ in range(5)], "Kraj": [datetime(2024, 1, 1, 0, 0) for _ in range(5)]})   
            tabela = st.data_editor(data_tabela, column_config={"Projekat": st.column_config.SelectboxColumn("Projekat", options=[i['name'] for i in jobs.find()]), "Zadatak": st.column_config.SelectboxColumn("Zadatak", options=list(alltasks.keys())), "Pocetak": st.column_config.DatetimeColumn("Pocetak", format="ddd MMM DD HH:mm:ss YYYY"), "Kraj": st.column_config.DatetimeColumn("Kraj", format="ddd MMM DD HH:mm:ss YYYY")}, use_container_width=True, hide_index=True)
            if st.button("Sačuvaj"):
                try:
                    test = st.session_state.tabela
                except Exception:
                    st.session_state.tabela = {}
                if st.session_state.tabela != tabela.to_dict():
                    for i in range(5):
                        if tabela["Projekat"][i] != None and tabela["Projekat"][i] != "" and tabela["Zadatak"][i] != None and tabela["Zadatak"][i] != "":
                            update_list = jobs.find_one({"name": tabela['Projekat'][i]})[alltasks[tabela["Zadatak"][i]]]
                            update_list.append({"person": w, "time": [(date_encode(tabela["Pocetak"][i]), date_encode(tabela["Kraj"][i]))]})
                            jobs.update_one({"name": tabela["Projekat"][i]}, {"$set": {alltasks[tabela["Zadatak"][i]]: update_list}})
                    st.success("Uspešno sačuvan")
                    st.session_state.tabela = tabela.to_dict()

        with active_projects:
            active_proj = st.selectbox("Izaberi projekat", [x['name'] for x in jobs.find()])
            st.divider()
            jobs_list = [0 for _ in range(len(list(alltasks.values())))]
            with st.expander("Vreme po radniku"):
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
                                        Sati: {round(v, 2)} = {round(v, 2)*accs.find_one({"name": i})['sat']} din""")

            st.divider()
            with st.expander("Vreme po zadatku"):
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
                        st.write(f"Ukupno - {round(v_uk, 2)}h = {round(sum(jobs_list), 2)} din")
                    else:
                        st.write(f"{alltasks_inv[k]} - {round(v, 2)}h = {round(jobs_list[index], 2)} din")
                    st.divider()
            st.divider()             


        with stats:
            person = st.selectbox("Izaberi radnika", workers)
            tasks = []
            times = []
            data = {'Radni sati':[], 'Komentar': []}
            data1 = {'Radni sati': [], 'Komentar': []}
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
            index = [x for x in range(1, calendar.monthrange(year, month)[1]+1)] + ["Ukupno"]
            index1 = [x for x in range(1, calendar.monthrange(year1, month1)[1]+1)] + ["Ukupno"]
            data["Komentar"] = [" " for _ in range(len(index))]
            data1["Komentar"] = [" " for _ in range(len(index1))]
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

                    data["Radni sati"].append(round(s, 2))
                
                for i in index1[:-1]:
                    s = 0
                    for j in times:
                        if i == date_decode(j[1]).day and month1 == date_decode(j[1]).month and year1 == date_decode(j[1]).year:
                            r = date_decode(j[1]) - date_decode(j[0])
                            try:
                                s+=(r.seconds/3600)
                            except Exception:
                                pass

                    data1["Radni sati"].append(round(s, 2))

                data["Radni sati"].append(round(sum(data["Radni sati"]), 2))
                data1["Radni sati"].append(round(sum(data1["Radni sati"]), 2))
                df = pd.DataFrame(data=data, index=index)
                df1 = pd.DataFrame(data=data1, index=index1)

                try:
                    old_df = pd.read_excel(f"data/{person}_{month}_{year}.xlsx")
                    test = old_df.to_dict()["Komentar"]
                except Exception:
                    df.to_excel(f"data/{person}_{month}_{year}.xlsx")
                else:
                    comentar = list(old_df.to_dict()["Komentar"].values())
                    data["Komentar"] = comentar
                    df = pd.DataFrame(data=data, index=index)
                    df.to_excel(f"data/{person}_{month}_{year}.xlsx")
                

                buffer = io.BytesIO()
                buffer1 = io.BytesIO()

                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Sheet1")


                with pd.ExcelWriter(buffer1, engine="xlsxwriter") as writer:
                    df1.to_excel(writer, sheet_name="Sheet1")

                st.download_button("Tabela radnih sati prethodnog meseca", data=buffer1, mime="application/vnd.ms-excel", file_name=f"{person}_{month1}_{year1}.xlsx")
                st.download_button("Tabela radnih sati ovog meseca", data=buffer, mime="application/vnd.ms-excel", file_name=f"{person}_{month}_{year}.xlsx")
                
                with st.expander("Dodaj komentar"):
                    with st.form("change_of_worksheet"):
                        st.subheader(f"{month}_{year}")
                        data["Index"] = index
                        u_worksheet = st.data_editor(data, disabled=["Index", "Radni sati"], column_order=["Index", "Radni sati", "Komentar"], use_container_width=True)
                        if st.form_submit_button("Primeni"):
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
            name = st.text_input("Ime projekta")
            if st.button("Napravi projekat") and name and jobs.find_one({"name": name}) is None:
                new_dict = {"name": name}
                for i in list(alltasks.values()):
                    new_dict[i] = []
                jobs.insert_one(new_dict)
                st.success("Novi projekat je napravljen")

        with create_accs:
            tmp = st.empty().container()
            with tmp.form("create_accs"):
                user_name = st.text_input("Ime i prezime")
                user_role = st.selectbox("Izaberi ulogu naloga", ['administrator', "radnik"])
                user_sat = st.number_input("Satnica")
                if st.form_submit_button("Napravi nalog") and user_name and user_role and user_sat:
                    if user_role == "administrator":
                        accs.insert_one({"name": user_name, "role": "admin", "sat": user_sat})
                    else:
                        accs.insert_one({"name": user_name, "role": "worker", "sat": user_sat})
                    st.success("Nalog je napravljen")

        with remove:
            tmp2 = st.empty()
            tmp3 = st.empty()
            with tmp2.container():
                remove_select = st.selectbox("Šta želite da uklonite?", ["Naloge", "Projekte", "Zadatak"])
                stuff = []
                if remove_select == "Naloge":
                    for i in accs.find({"role": {"$ne": "admin"}}):
                        stuff.append((st.checkbox(i['name']), i['name']))
                    if st.button("Ukloni"):
                        tmp2.empty()
                        with tmp3.container():
                            st.write("Da li ste sigurni?")
                            st.button("Da", on_click=remove_accs, args=(stuff, ))
                            st.button("Ne")
                
                if remove_select == "Projekte":
                    for i in jobs.find():
                        stuff.append((st.checkbox(i['name']), i['name']))
                    if st.button("Ukloni"):
                        tmp2.empty()
                        with tmp3.container():
                            st.write("Da li ste sigurni?")
                            st.button("Da", on_click=remove_proj, args=(stuff, ))
                            st.button("Ne")

                if remove_select == "Zadatak":
                    project = st.selectbox("Izaberite projekat", [x['name'] for x in jobs.find()])
                    project_object = jobs.find_one({"name": project})
                    for i in list(alltasks.values()):
                        for index, j in enumerate(project_object[i]):
                            stuff.append((st.checkbox(f"{j['person']} - {project} - {alltasks_inv[i]} - {j['time'][0][0]} - {j['time'][0][1]}", key=str(index)+str(j)+i), j, i, project))
                    if st.button("Ukloni"):
                        tmp2.empty()
                        with tmp3.container():
                            st.write("Da li ste sigurni?")
                            st.button("Da", on_click=remove_task, args=(stuff, ))
                            st.button("Ne")
                        st.rerun()

if __name__ == "__main__":
    if c['logged'] == 'false':
        with tmp.form("log"):
            user = st.text_input("Korisničko ime")
            if st.form_submit_button("Uloguj se"):
                accs = con.main.accounts
                tmp_acc = accs.find_one({"user": user})
                if tmp_acc['user']  == user and tmp_acc['role'] == "admin":
                    tmp.empty()
                    c['logged'] = 'true'
                    c['user'] = user
                    c['name'] = accs.find_one({"user": user})['name']
                    c['r'] = accs.find_one({"user": user})['role']
                else:
                    st.error("Pogrešno korisničko ime")
    if c['logged'] == 'true':
        run()

