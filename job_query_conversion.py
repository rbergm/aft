
import pathlib

job_dir = pathlib.Path("job")
job_queries = job_dir.glob("[0-9]*sql")

contents = []

for job_file in job_queries:
    with job_file.open("r") as job_query:
        query = job_query.readline()
        #print(job_file, query)
        #job_query.truncate(0)
        #job_query.write("explain (analyze, format json) " + query)
        contents.append("explain (analyze, format json) " + query)

with open("job-complete.sql", "w") as outfile:
    outfile.writelines(contents)
