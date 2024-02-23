from flask import Flask, render_template, request, jsonify, send_file,redirect
import psycopg2
from datetime import datetime, timedelta
import pandas as pd
import os

app = Flask(__name__)

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='qualification_accounting',
    user='postgres',
    password='60HQztth3fDW',
)
cur = conn.cursor()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def submit_form():
    if request.method == 'POST':
        
        name = request.form['name']
        course = request.form['course']
        date = request.form['date']
        hours = request.form['hours']
        credits = request.form['credits']
        country = request.form['country']
        type = request.form['type']
        
      
        if 'certificate' in request.files:
            file = request.files['certificate']
            
            file_data = file.read()
        else:
            file_data = None

       
        cur.execute("""
        INSERT INTO teach_info (person, name_of_course, date, hours, ects_credits, certificate, country, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, course, date, hours, credits, file_data, country, type))

        conn.commit()

        
        cur.execute("""
        DELETE FROM teach_info
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY person, name_of_course, ects_credits ORDER BY id) AS rnum
                FROM teach_info
            ) t
            WHERE t.rnum > 1
        );
        """)
        
       
        cur.execute("SELECT DISTINCT person, name_of_course, ects_credits FROM teach_info WHERE person = %s", (name,))
        
        rows = cur.fetchall()

        
        return render_template('index.html', rows=rows)
    else:
        return 'Form submission failed.'

@app.route('/delete_row', methods=['POST'])
def delete_row():
    if request.method == 'POST':
        try:
            
            name_of_course = request.form['name_of_course']
            
           
            cur.execute("DELETE FROM teach_info WHERE name_of_course = %s", (name_of_course,))
            
            conn.commit()
        except Exception as e:
         
            conn.rollback()  
            print("Error deleting row:", e)
        
       
        return redirect('/')



@app.route('/submit1', methods=['POST'])
def submit1():
    name = request.form['name']

    reference_date = datetime(2024, 4, 20)
    five_years_ago = reference_date - timedelta(days=5*365)
    cur.execute("""
        DELETE FROM teach_info
        WHERE teach_info.date < %s
    """, (five_years_ago,))

    cur.execute("""
        INSERT INTO total_ects_table (person, ects_total)
        SELECT person, SUM(ects_credits)
        FROM teach_info
        WHERE person = %s
        GROUP BY person
    """, (name,))

    conn.commit()

    return redirect('/')


#reports.html

@app.route('/reports.html')
def show_reports():
    return render_template('reports.html')


def get_data_from_database():
    cursor = conn.cursor()
    cursor.execute("SELECT person, name_of_course, hours, ects_credits, country, type FROM teach_info")
    data = cursor.fetchall()
    cursor.close()
    return data

def create_excel_report(data):
    df = pd.DataFrame(data, columns=['person', 'name_of_course', 'hours', 'ects_credits', 'country', 'type', 'ects_total'])
    excel_filename = 'report.xlsx'
    writer = pd.ExcelWriter(excel_filename, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    
    worksheet.set_column('A:A', 28.76)  # person
    worksheet.set_column('B:B', 33.33)  # name_of_course
    worksheet.set_column('C:C', 8.11)   # hours
    worksheet.set_column('D:D', 13.56)  # ects_credits
    worksheet.set_column('E:E', 10)     # country
    worksheet.set_column('F:F', 10)     # type
    worksheet.set_column('G:G', 13.56)  # ects_total
    
    font_format = workbook.add_format({'font_name': 'Arial', 'font_size': 12})
    bold_format = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True})  
    
    worksheet.set_row(0, cell_format=font_format)  

   
    for row_num, row_data in enumerate(data):
        if row_num == 0:
            bold_range = f'G{row_num+2}'  
            worksheet.write(bold_range, row_data[6], bold_format)  
        else:
            worksheet.write(row_num + 1, 6, row_data[6], font_format) 
    
    writer.close()
    return excel_filename



@app.route('/')
def index():
    return render_template('reports.html')

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    search_term = request.args.get('term')
    cur.execute("SELECT DISTINCT person FROM teach_info WHERE person ILIKE %s", ('%' + search_term + '%',))
    results = [row[0] for row in cur.fetchall()]
    return jsonify(results)

@app.route('/search-form', methods=['POST'])
def search_form():
    search_input = request.form['search-input']

    cur.execute("""
    SELECT 
        teach_info.person, 
        teach_info.name_of_course, 
        teach_info.hours, 
        teach_info.ects_credits, 
        teach_info.country, 
        teach_info.type,
        total_ects_table.ects_total
    FROM 
        teach_info
    JOIN 
        total_ects_table ON teach_info.person = total_ects_table.person
    WHERE 
        teach_info.person= %s
    """, (search_input,))

    result = cur.fetchall()

    excel_filename = create_excel_report(result)

    return render_template('reports.html', data=result, excel_link='/download_report')

@app.route('/download_report')
def download_report():
    filename = 'report.xlsx'
    directory = os.getcwd()
    path = os.path.join(directory, filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)


