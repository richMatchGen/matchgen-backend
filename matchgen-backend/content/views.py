# ... existing code ...

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def import_fa_fixtures(request):
    """
    Import fixtures from FA Fulltime page
    """
    try:
        data = json.loads(request.body)
        url = data.get('url')
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        # Validate FA Fulltime URL
        if 'fulltime.thefa.com' not in url:
            return JsonResponse({'error': 'Invalid FA Fulltime URL'}, status=400)
        
        # Scrape fixtures from FA Fulltime
        fixtures = scrape_fa_fixtures(url)
        
        if not fixtures:
            return JsonResponse({'error': 'No fixtures found on the page'}, status=404)
        
        # Create fixtures in database
        created_count = 0
        for fixture_data in fixtures:
            try:
                match = Match.objects.create(
                    match_type=fixture_data.get('match_type', 'League'),
                    opponent=fixture_data.get('opponent', ''),
                    date=fixture_data.get('date'),
                    time_start=fixture_data.get('time'),
                    venue=fixture_data.get('venue', 'Home'),
                    home_away=fixture_data.get('home_away', 'HOME'),
                    competition=fixture_data.get('competition', ''),
                    notes=fixture_data.get('notes', '')
                )
                created_count += 1
            except Exception as e:
                logger.error(f"Error creating fixture: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'count': created_count,
            'message': f'Successfully imported {created_count} fixtures'
        })
        
    except Exception as e:
        logger.error(f"Error importing FA fixtures: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def import_cricket_fixtures(request):
    """
    Import fixtures from Play Cricket API
    """
    try:
        data = json.loads(request.body)
        url = data.get('url')
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        # Validate Play Cricket URL
        if 'play-cricket.ecb.co.uk' not in url:
            return JsonResponse({'error': 'Invalid Play Cricket URL'}, status=400)
        
        # Extract site ID from URL
        site_id = extract_site_id_from_url(url)
        if not site_id:
            return JsonResponse({'error': 'Could not extract site ID from URL'}, status=400)
        
        # Fetch fixtures from Play Cricket API
        fixtures = fetch_cricket_fixtures(site_id)
        
        if not fixtures:
            return JsonResponse({'error': 'No fixtures found'}, status=404)
        
        # Create fixtures in database
        created_count = 0
        for fixture_data in fixtures:
            try:
                match = Match.objects.create(
                    match_type=fixture_data.get('match_type', 'League'),
                    opponent=fixture_data.get('opponent', ''),
                    date=fixture_data.get('date'),
                    time_start=fixture_data.get('time'),
                    venue=fixture_data.get('venue', 'Home'),
                    home_away=fixture_data.get('home_away', 'HOME'),
                    competition=fixture_data.get('competition', ''),
                    notes=fixture_data.get('notes', '')
                )
                created_count += 1
            except Exception as e:
                logger.error(f"Error creating fixture: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'count': created_count,
            'message': f'Successfully imported {created_count} fixtures'
        })
        
    except Exception as e:
        logger.error(f"Error importing cricket fixtures: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def scrape_fa_fixtures(url):
    """
    Scrape fixtures from FA Fulltime page
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        fixtures = []
        
        # Look for fixture tables or lists
        fixture_rows = soup.find_all('tr', class_=re.compile(r'fixture|match'))
        
        for row in fixture_rows:
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                # Extract fixture data based on common FA Fulltime structure
                opponent = extract_opponent_from_cells(cells)
                date = extract_date_from_cells(cells)
                time = extract_time_from_cells(cells)
                venue = extract_venue_from_cells(cells)
                competition = extract_competition_from_cells(cells)
                
                if opponent and date:
                    fixtures.append({
                        'opponent': opponent,
                        'date': date,
                        'time': time,
                        'venue': venue,
                        'competition': competition,
                        'match_type': 'League',
                        'home_away': 'HOME' if 'home' in venue.lower() else 'AWAY',
                        'notes': f'Imported from FA Fulltime'
                    })
            except Exception as e:
                logger.error(f"Error parsing fixture row: {e}")
                continue
        
        return fixtures
        
    except Exception as e:
        logger.error(f"Error scraping FA fixtures: {e}")
        return []

def extract_opponent_from_cells(cells):
    """Extract opponent name from table cells"""
    for cell in cells:
        text = cell.get_text().strip()
        if text and not any(keyword in text.lower() for keyword in ['date', 'time', 'venue', 'competition']):
            return text
    return ''

def extract_date_from_cells(cells):
    """Extract date from table cells"""
    for cell in cells:
        text = cell.get_text().strip()
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
            try:
                return datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                continue
    return ''

def extract_time_from_cells(cells):
    """Extract time from table cells"""
    for cell in cells:
        text = cell.get_text().strip()
        if re.match(r'\d{1,2}:\d{2}', text):
            return text
    return ''

def extract_venue_from_cells(cells):
    """Extract venue from table cells"""
    for cell in cells:
        text = cell.get_text().strip()
        if any(keyword in text.lower() for keyword in ['home', 'away', 'venue']):
            return text
    return 'Home'

def extract_competition_from_cells(cells):
    """Extract competition from table cells"""
    for cell in cells:
        text = cell.get_text().strip()
        if any(keyword in text.lower() for keyword in ['league', 'cup', 'friendly']):
            return text
    return ''

def extract_site_id_from_url(url):
    """Extract site ID from Play Cricket URL"""
    try:
        # Common patterns for Play Cricket URLs
        patterns = [
            r'/website/web_pages/(\d+)',
            r'/website/(\d+)',
            r'id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    except:
        return None

def fetch_cricket_fixtures(site_id):
    """
    Fetch fixtures from Play Cricket API
    """
    try:
        # Play Cricket API endpoints
        api_base = 'https://play-cricket.com/api/v2'
        
        # Get upcoming matches
        matches_url = f"{api_base}/matches.json?site_id={site_id}&from_date={datetime.now().strftime('%Y-%m-%d')}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(matches_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        fixtures = []
        
        if 'matches' in data:
            for match in data['matches']:
                try:
                    # Extract fixture data from API response
                    opponent = match.get('opponent_name', '')
                    match_date = match.get('match_date', '')
                    match_time = match.get('match_time', '')
                    venue = match.get('ground_name', 'Home')
                    competition = match.get('competition_name', '')
                    
                    if opponent and match_date:
                        fixtures.append({
                            'opponent': opponent,
                            'date': match_date,
                            'time': match_time,
                            'venue': venue,
                            'competition': competition,
                            'match_type': 'League',
                            'home_away': 'HOME' if match.get('home_away') == 'H' else 'AWAY',
                            'notes': f'Imported from Play Cricket'
                        })
                except Exception as e:
                    logger.error(f"Error processing cricket match: {e}")
                    continue
        
        return fixtures
        
    except Exception as e:
        logger.error(f"Error fetching cricket fixtures: {e}")
        return []