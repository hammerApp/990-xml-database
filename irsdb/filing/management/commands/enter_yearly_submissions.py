import csv
import os
import requests

from django.core.management.base import BaseCommand
from filing.models import Filing
from django.conf import settings
import sys
sys.path.append('../../../../990-xml-reader')
from irs_reader.settings import INDEX_DIRECTORY
from irs_reader.file_utils import stream_download

BATCH_SIZE = 10000


class Command(BaseCommand):
    help = '''
    Read the yearly csv file line by line and add new lines if
    they don't exist. Lines are added in bulk at the end.
    '''

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('year', nargs='+', type=str)

    def handle(self, *args, **options):
        for year in options['year']:
            local_file_path = os.path.join(INDEX_DIRECTORY, "index_%s.csv" % year)


            print("Entering xml submissions from %s" % local_file_path)
            fh = open(local_file_path, 'r',encoding='utf-8-sig')
            reader = csv.DictReader(fh)
            rows_to_enter = []

            count = 0
            for line in reader:
                try:
                    if "OBJECT_ID" in line.keys():
                        # sometimes there's an empty extra column, ignore it
                        # RETURN_ID,EIN,TAX_PERIOD,SUB_DATE,TAXPAYER_NAME,RETURN_TYPE,DLN,OBJECT_ID
                        return_id = line['RETURN_ID']
                        filing_type = line['FILING_TYPE']
                        ein = line['EIN']
                        tax_period = line['TAX_PERIOD']
                        sub_date = line['SUB_DATE']
                        taxpayer_name = line['TAXPAYER_NAME']
                        return_type = line['RETURN_TYPE']
                        dln = line['DLN']
                        object_id = line['OBJECT_ID']
                        sub_year = year
                        # (return_id,filing_type, ein, tax_period, sub_date, taxpayer_name, return_type, dln, object_id) = line[0:8]
                        #print(return_id, ein, tax_period, sub_date, taxpayer_name, return_type, dln, object_id)
                    else:
                        return_id = ""
                        filing_type = "EFILE"
                        ein = line['ein']
                        tax_period = line['tax_prd']
                        sub_date = line['submitted_on']
                        taxpayer_name = line['organization_name']
                        return_type = line['formtype_str']
                        dln = line['dln']
                        object_id = line['object_id']
                        try:
                            sub_year = line['year']
                        except Exception as e:
                            sub_year = int(year.replace("new_",""))

                except ValueError as err:
                    print("Error with line: {line}".format(line=line))
                    if year == 2014:
                        print('Did you fix the 2014 index file? See the README for instructions.')
                    raise

                try:
                    obj = Filing.objects.get(object_id=object_id)
                except Filing.DoesNotExist:
                    new_sub = Filing(
                        return_id=return_id,
                        submission_year=sub_year,
                        filing_type=filing_type,
                        ein=ein,
                        tax_period=tax_period,
                        sub_date=sub_date,
                        taxpayer_name=taxpayer_name,
                        return_type=return_type,
                        dln=dln,
                        object_id=object_id
                    )

                    rows_to_enter.append(new_sub)
                    count += 1

                if count % BATCH_SIZE == 0 and count > 0:
                    print("Committing %s total entered=%s" % (BATCH_SIZE, count))
                    Filing.objects.bulk_create(rows_to_enter)
                    print("commit complete")
                    rows_to_enter = []

            Filing.objects.bulk_create(rows_to_enter)
            print("Added %s new entries." % count)
