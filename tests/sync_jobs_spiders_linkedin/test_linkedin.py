from datetime import date, timedelta
from pathlib import Path

import pytest
from scrapy.http import HtmlResponse

from juniorguru.sync.jobs.spiders import linkedin


FIXTURES_DIR = Path(__file__).parent


def test_spider_parse():
    response = HtmlResponse('https://example.com/seeMoreJobPostings/',
                            body=Path(FIXTURES_DIR / 'more.html').read_bytes())
    requests = list(linkedin.Spider().parse(response))
    job_requests = list(filter(lambda r: '/jobPosting/' in r.url, requests))
    more_requests = list(filter(lambda r: '/seeMoreJobPostings/' in r.url, requests))

    assert len(job_requests) == 25
    assert job_requests[0].url == 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/1846698040'

    assert len(more_requests) == 1
    assert 'start=25' in more_requests[0].url


def test_spider_parse_end():
    response = HtmlResponse('https://example.com/seeMoreJobPostings/',
                            body=Path(FIXTURES_DIR / 'more_end.html').read_bytes())
    requests = list(linkedin.Spider().parse(response))
    job_requests = list(filter(lambda r: '/jobPosting/' in r.url, requests))
    more_requests = list(filter(lambda r: '/seeMoreJobPostings/' in r.url, requests))

    assert len(job_requests) == 21
    assert len(more_requests) == 0


def test_spider_parse_job():
    response = HtmlResponse('https://example.com/example/',
                            body=Path(FIXTURES_DIR / 'job.html').read_bytes())
    jobs = list(linkedin.Spider().parse_job(response))

    assert len(jobs) == 1

    job = jobs[0]

    assert sorted(job.keys()) == sorted([
        'title', 'link', 'company_name', 'company_link', 'locations_raw',
        'employment_types', 'posted_at', 'description_html',
        'experience_levels', 'company_logo_urls', 'remote',
    ])
    assert job['title'] == 'Junior BI Developer (BI4SG)'
    assert job['link'] == 'https://cz.linkedin.com/jobs/view/junior-bi-developer-bi4sg-at-komer%C4%8Dn%C3%AD-banka-2701029809'
    assert job['company_name'] == 'Komerční banka'
    assert job['company_link'] == 'https://cz.linkedin.com/company/komercni-banka'
    assert job['locations_raw'] == ['Prague, Czechia']
    assert job['remote'] is False
    assert job['employment_types'] == ['full-time']
    assert job['experience_levels'] == ['entry level']
    assert job['posted_at'] == date.today() - timedelta(weeks=1)
    assert job['company_logo_urls'] == ['https://media-exp1.licdn.com/dms/image/C560BAQHxuVQO-Rz9rw/company-logo_100_100/0/1546508771908?e=1640217600&v=beta&t=hUZKjJ2dnPP92AcBOKAEFzFqEdD-OB9WwS0X18LoyP4']
    assert '<li>French language</li>' in job['description_html']


@pytest.mark.skip('missing a test fixture')
def test_spider_parse_job_description_doesnt_include_criteria_list():
    response = HtmlResponse('https://example.com/example/',
                            body=Path(FIXTURES_DIR / 'job.html').read_bytes())
    job = next(linkedin.Spider().parse_job(response))

    assert 'Employment type' not in job['description_html']
    assert 'Information Technology and Services' not in job['description_html']


def test_spider_parse_job_no_company_link():
    response = HtmlResponse('https://example.com/example/',
                            body=Path(FIXTURES_DIR / 'job_no_company_link.html').read_bytes())
    job = next(linkedin.Spider().parse_job(response))

    assert job['company_name'] == 'NeoTreks, Inc.'
    assert 'company_link' not in job
    assert job['locations_raw'] == ['Frýdek-Místek, Moravia-Silesia, Czechia']


def test_spider_parse_job_company_logo():
    response = HtmlResponse('https://example.com/example/',
                            body=Path(FIXTURES_DIR / 'job_company_logo.html').read_bytes())
    job = next(linkedin.Spider().parse_job(response))

    assert job['company_logo_urls'] == ['https://media-exp1.licdn.com/dms/image/C4D0BAQE5dJwgWcSH0g/company-logo_100_100/0/1545137392551?e=1640217600&v=beta&t=iVYrn2ljyLGyu53ggzJr7fZ-aTJPfvzTczAfdgsJYTU']


def test_spider_parse_job_apply_on_company_website():
    response = HtmlResponse('https://example.com/example/',
                            body=Path(FIXTURES_DIR / 'job_apply_on_company_website.html').read_bytes())
    request = next(linkedin.Spider().parse_job(response))
    job = request.cb_kwargs['item']

    assert job['link'] == 'https://cz.linkedin.com/jobs/view/junior-automation-test-engineer-for-siemens-at-siemens-2689458333'
    assert job['alternative_links'] == ['https://jobs.siemens.com/jobs/240215?lang=en-us&jobPipeline=juniorguru%3FsourceType%3DPREMIUM_POST_SITE&source=juniorguru%28Wrap%29']


def test_spider_verify_job_apply_on_company_website():
    response = HtmlResponse('https://example.com/example/', body=b'')
    item = dict(link='https://cz.linkedin.com/jobs/view/junior-automation-test-engineer-for-siemens-at-siemens-2689458333',
                alternative_links=['https://example.com/example/?redirect=foo'])
    job = next(linkedin.Spider().verify_job(response, item))

    assert job['link'] == 'https://example.com/example/'
    assert job['alternative_links'] == ['https://cz.linkedin.com/jobs/view/junior-automation-test-engineer-for-siemens-at-siemens-2689458333']


def test_clean_proxied_url():
    url = (
        'https://cz.linkedin.com/jobs/view/externalApply/2006390996'
        '?url=https%3A%2F%2Fjobs%2Egecareers%2Ecom%2Fglobal%2Fen%2Fjob%2FGE11GLOBAL32262%2FEngineering-Trainee%3Futm_source%3Dlinkedin%26codes%3DLinkedIn%26utm_medium%3Dphenom-feeds'
        '&urlHash=AAbh&refId=94017428-1cc1-48ad-bda2-d9ddabeb1c55&trk=public_jobs_apply-link-offsite'
    )

    assert linkedin.clean_proxied_url(url) == 'https://jobs.gecareers.com/global/en/job/GE11GLOBAL32262/Engineering-Trainee?codes=juniorguru'


def test_get_job_id():
    url = (
        'https://cz.linkedin.com/jobs/view/'
        'junior-software-engineer-at-cimpress-technology-2247016723'
    )

    assert linkedin.get_job_id(url) == '2247016723'


@pytest.mark.parametrize('url,expected', [
    ('https://uk.linkedin.com/company/adaptavist?trk=public_jobs_topcard_logo', 'https://uk.linkedin.com/company/adaptavist'),
    ('https://example.com?trk=123', 'https://example.com?trk=123'),
    ('https://pipedrive.talentify.io/job/junior-software-engineer-prague-prague-pipedrive-015b84ef-3956-4a28-877f-0385379d40c2?tdd=dDEsaDM1LGozdXFlZSxlcHJvNjA3ZjBhOTA2ZDVkNjE2OTQ4ODk3OA', 'https://pipedrive.talentify.io/job/junior-software-engineer-prague-prague-pipedrive-015b84ef-3956-4a28-877f-0385379d40c2'),
    ('https://neuvoo.cz/job.php?id=b5f15b6eeadc&source=juniorguru&puid=aadegddb8adaeddfeddb9ade7ddafadbaadbfadf3aeccacdfec3ddcg3e', 'https://neuvoo.cz/job.php?id=b5f15b6eeadc&source=juniorguru'),
    ('https://jobs.lever.co/pipedrive/015b84ef-3956-4a28-877f-0385379d40c2/apply', 'https://jobs.lever.co/pipedrive/015b84ef-3956-4a28-877f-0385379d40c2/'),
    ('https://erstegroup-careers.com/csas/job/Hlavn%C3%AD-m%C4%9Bsto-Praha-Tester-EOM/667861301/?locale=cs_CZ&utm_campaign=lilimitedlistings&utm_source=lilimitedlistings&applySourceOverride=Linkedin%20Limited%20Listings', 'https://erstegroup-careers.com/csas/job/Hlavn%C3%AD-m%C4%9Bsto-Praha-Tester-EOM/667861301/?locale=cs_CZ&applySourceOverride=juniorguru+Limited+Listings'),
])
def test_clean_url(url, expected):
    assert linkedin.clean_url(url) == expected


@pytest.mark.parametrize('text,expected', [
    ('Junior Software Engineer (C#.NET)', False),
    ('Remote Web Developer - Prague', True),
    ('Remote Web Developer', True),
])
def test_parse_remote(text, expected):
    assert linkedin.parse_remote(text) is expected
