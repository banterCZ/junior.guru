import os
from pathlib import Path

from juniorguru.lib import google_sheets, loggers
from juniorguru.lib.club import parse_coupon
from juniorguru.lib.coerce import (coerce, parse_boolean_words, parse_date, parse_int,
                                   parse_text)
from juniorguru.lib.images import render_image_file
from juniorguru.cli.sync import main as cli
from juniorguru.models.base import db
from juniorguru.models.company import Company


logger = loggers.from_path(__file__)


FLUSH_POSTERS_COMPANIES = bool(int(os.getenv('FLUSH_POSTERS_COMPANIES', 0)))
IMAGES_DIR = Path(__file__).parent.parent / 'images'
POSTERS_DIR = IMAGES_DIR / 'posters-companies'

POSTER_WIDTH = 700
POSTER_HEIGHT = 700


@cli.sync_command()
@db.connection_context()
def main():
    if FLUSH_POSTERS_COMPANIES:
        logger.warning("Removing all existing posters for companies, FLUSH_POSTERS_COMPANIES is set")
        for poster_path in POSTERS_DIR.glob('*.png'):
            poster_path.unlink()

    doc_key = '1TO5Yzk0-4V_RzRK5Jr9I_pF5knZsEZrNn2HKTXrHgls'
    records = google_sheets.download(google_sheets.get(doc_key, 'companies'))

    Company.drop_table()
    Company.create_table()

    for record in records:
        logger.info('Saving a record')
        company = Company.create(**coerce_record(record))

        logger.info(f"Rendering images for {company!r}")
        tpl_context = dict(company=company)
        image_path = render_image_file(POSTER_WIDTH, POSTER_HEIGHT,
                                       'company.html', tpl_context, POSTERS_DIR)
        company.poster_path = image_path.relative_to(IMAGES_DIR)
        company.save()


def coerce_record(record):
    data = coerce({
        r'^name$': ('name', parse_text),
        r'^email$': ('email', parse_text),
        r'^filename$': ('logo_filename', parse_text),
        r'^handbook$': ('is_sponsoring_handbook', parse_boolean_words),
        r'^student coupon$': ('student_coupon', parse_text),
        r'^link$': ('url', parse_text),
        r'^coupon$': ('coupon', parse_text),
        r'^starts$': ('starts_on', parse_date),
        r'^expires$': ('expires_on', parse_date),
        r'^job slots$': ('job_slots_count', parse_int),
    }, record)
    if data.get('coupon'):
        data['slug'] = parse_slug(data['coupon'])
    return data


def parse_slug(coupon):
    if coupon:
        return parse_coupon(coupon)['name'].lower()
    return None
