
"""Télécharge les JSON Insee Melodi de 2023 pour quatre régions.


"""
import argparse
import csv
import gzip
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

YEAR = '2023'
REGIONS = {'11': 'ile_de_france', '53': 'bretagne', '76': 'occitanie', '84': 'auvergne_rhone_alpes'}
DATASETS = (
    'DS_RP_POPULATION_PRINC',
    'DS_RP_EMPLOI_LR_PRINC',
    'DS_RP_DIPLOMES_PRINC',
    'DS_RP_MENAGES_PRINC',
    'DS_RP_LOGEMENT_PRINC',
    'DS_FILOSOFI_CC',
    'DS_POPULATIONS_HISTORIQUES',
)
COG_URL = 'https://www.insee.fr/fr/statistiques/fichier/8740222/v_commune_2026.csv'
API_URL = 'https://api.insee.fr/melodi/data'
OUTPUT = Path(__file__).resolve().parents[2] / 'bronze' / 'insee'
BATCH_SIZE = 200
PAGE_SIZE = 100000
MAX_URL_LENGTH = 3500
WAIT_SECONDS = 2.1  # API publique : 30 appels/minute.
MAX_ATTEMPTS = 5
TIMEOUT_SECONDS = 60


def decode(raw):
    def invalid(value):
        raise ValueError('Constante JSON interdite : ' + value)
    return json.loads(raw, parse_constant=invalid)


def official(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or not (parts.hostname == 'insee.fr' or (parts.hostname or '').endswith('.insee.fr')) or parts.username or parts.password:
        raise ValueError('URL non officielle : ' + url)
    return url


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(OfficialRedirect())
        self.last_call = 0.0

    def get(self, url):
        official(url)
        for attempt in range(MAX_ATTEMPTS):
            time.sleep(max(0.0, WAIT_SECONDS - (time.monotonic() - self.last_call)))
            self.last_call = time.monotonic()
            try:
                request = urllib.request.Request(url, headers={'Accept-Encoding': 'gzip', 'User-Agent': 'DS4SC-Insee-2023/1.0'})
                with self.opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                    official(response.url)
                    raw = response.read()
                    encoding = response.headers.get('Content-Encoding', 'identity').lower()
                if encoding == 'gzip':
                    raw = gzip.decompress(raw)  # Décompression HTTP ; JSON non réencodé.
                elif encoding != 'identity':
                    raise ValueError('Encodage HTTP inconnu : ' + encoding)
                if not raw.strip():
                    raise ValueError('Réponse vide')
                return raw
            except urllib.error.HTTPError as exc:
                if exc.code not in (408, 429) and exc.code < 500:
                    raise RuntimeError('HTTP %s pour %s' % (exc.code, url)) from exc
                retry_after = exc.headers.get('Retry-After', '')
                try:
                    delay = max(float(retry_after), 2 ** (attempt + 1))
                except ValueError:
                    delay = 2 ** (attempt + 1)
                error = 'HTTP %s' % exc.code
            except (urllib.error.URLError, OSError, EOFError, ValueError) as exc:
                delay = 2 ** (attempt + 1)
                error = str(exc)
            if attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError('%s : %s tentatives épuisées' % (error, MAX_ATTEMPTS))
            print('Nouvelle tentative dans %.0f s : %s' % (delay, error), flush=True)
            time.sleep(delay)


def communes(client):
    rows = csv.DictReader(io.StringIO(client.get(COG_URL).decode('utf-8-sig')))
    if not {'TYPECOM', 'COM', 'REG'}.issubset(rows.fieldnames or []):
        raise ValueError('Colonnes COG inattendues')
    result = {code: [] for code in REGIONS}
    for row in rows:
        if row['TYPECOM'] == 'COM' and row['REG'] in result:
            code = row['COM']  # Toujours du texte : conserve les zéros initiaux.
            if not re.fullmatch(r'[0-9A-Z]{5}', code):
                raise ValueError('Code commune invalide : ' + code)
            result[row['REG']].append('COM-' + code)
    for region, codes in result.items():
        codes.sort()
        if not codes or len(set(codes)) != len(codes):
            raise ValueError('Liste COG vide ou dupliquée : ' + region)
    return result


def first_url(dataset, geos):
    params = [('GEO', geo) for geo in geos]
    params += [('TIME_PERIOD', YEAR), ('page', '1'), ('totalCount', 'true'), ('maxResult', str(PAGE_SIZE))]
    return API_URL + '/' + dataset + '?' + urllib.parse.urlencode(params)


def batches(dataset, geos):
    current = []
    for geo in geos:
        if current and (len(current) >= BATCH_SIZE or len(first_url(dataset, current + [geo])) > MAX_URL_LENGTH):
            yield current
            current = []
        current.append(geo)
        if len(first_url(dataset, current)) > MAX_URL_LENGTH:
            raise ValueError('URL trop longue pour une commune')
    if current:
        yield current


def check(doc, dataset, requested, url):
    if not isinstance(doc, dict) or doc.get('identifier') not in (dataset, dataset + '_2023'):
        raise ValueError('Identifiant du jeu inattendu')
    obs = doc.get('observations')
    if not isinstance(obs, list):
        raise ValueError('Champ observations absent')
    for item in obs:
        dims = item.get('dimensions', {})
        geo = str(dims.get('GEO', ''))
        match = re.fullmatch(r'(?:[0-9]{4}-)?(COM-[0-9A-Z]{5})', geo)
        if dims.get('TIME_PERIOD') != YEAR or not match or match.group(1) not in requested:
            raise ValueError('Observation hors de 2023 ou du lot : ' + str(dims))
    paging = doc.get('paging')
    if not isinstance(paging, dict) or not isinstance(paging.get('count'), int) or not isinstance(paging.get('isLast'), bool):
        raise ValueError('Pagination ou total absent')
    next_url = paging.get('next')
    if paging['isLast'] == bool(next_url):
        raise ValueError('Pagination incohérente')
    if next_url:
        next_url = urllib.parse.urljoin(url, next_url)
        official(next_url)
        current, following = urllib.parse.urlsplit(url), urllib.parse.urlsplit(next_url)
        if (current.netloc, current.path) != (following.netloc, following.path):
            raise ValueError('Lien next change de jeu')
        old = urllib.parse.parse_qs(current.query)
        new = urllib.parse.parse_qs(following.query)
        if {k: sorted(v) for k, v in old.items() if k != 'page'} != {k: sorted(v) for k, v in new.items() if k != 'page'}:
            raise ValueError('Lien next change les filtres')
        if new.get('page') != [str(int(old['page'][0]) + 1)]:
            raise ValueError('Boucle ou saut de pagination')
    return len(obs), paging['count'], next_url


def ingest_region(client, dataset, region, geos):
    folder = OUTPUT / dataset / ('region_' + region + '_' + REGIONS[region])
    folder.mkdir(parents=True, exist_ok=True)
    part_number = 0
    observations = 0
    for batch_number, group in enumerate(batches(dataset, geos), 1):
        url = first_url(dataset, group)
        seen = set()
        batch_count = 0
        announced = None
        while url:
            if url in seen:
                raise ValueError('Boucle de pagination')
            seen.add(url)
            part_number += 1
            path = folder / ('part_%04d.json' % part_number)
            if path.exists():
                raw = path.read_bytes()
            else:
                raw = client.get(url)
            doc = decode(raw)
            count, total, next_url = check(doc, dataset, set(group), url)
            if announced is not None and total != announced:
                raise ValueError('Total API modifié pendant la pagination')
            announced = total
            batch_count += count
            if not path.exists():
                tmp = path.with_suffix('.tmp')
                with tmp.open('wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                tmp.replace(path)  # Corps JSON reçu, octet pour octet.
            print('%s région %s lot %s page %s : %s observations' % (dataset, region, batch_number, len(seen), count), flush=True)
            url = next_url
        if batch_count != announced:
            raise ValueError('Lot incomplet : %s / %s observations' % (batch_count, announced))
        observations += batch_count
    actual = {p.name for p in folder.glob('part_*.json')}
    expected = {'part_%04d.json' % i for i in range(1, part_number + 1)}
    if actual != expected:
        raise ValueError('Pages en trop ou manquantes dans ' + str(folder))
    print('%s région %s : %s observations dans %s pages' % (dataset, region, observations, part_number), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', action='append', choices=REGIONS, help='Répéter pour plusieurs régions ; défaut : les quatre')
    parser.add_argument('--dataset', action='append', choices=DATASETS, help='Répéter pour plusieurs jeux ; défaut : les sept')
    args = parser.parse_args()
    client = Client()
    by_region = communes(client)
    for dataset in dict.fromkeys(args.dataset or DATASETS):
        for region in dict.fromkeys(args.region or REGIONS):
            ingest_region(client, dataset, region, by_region[region])


if __name__ == '__main__':
    main()
