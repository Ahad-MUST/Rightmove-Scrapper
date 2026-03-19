#!/usr/bin/env python3
"""
Rightmove Scraper - Production Flask Application
=================================================
Multi-user concurrent support with Celery + Redis
"""

import os
import sys

# Fix Python path for Celery worker imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from celery import Celery
from celery.result import AsyncResult

from dotenv import load_dotenv
load_dotenv()

# ── App Configuration ─────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# Celery configuration
app.config['CELERY_BROKER_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_TASK_TRACK_STARTED'] = True
app.config['CELERY_TASK_TIME_LIMIT'] = 3600  # 1 hour max per task

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# ── Load Data ─────────────────────────────────────────────────────────────────

with open('data/cities.json', 'r') as f:
    CITIES = json.load(f)

with open('data/city_areas.json', 'r') as f:
    CITY_AREAS = json.load(f)

# ── Authentication ────────────────────────────────────────────────────────────

VALID_USERS = {
    'admin': os.environ.get('ADMIN_PASSWORD', 'change_this_password'),
    # Add more users as needed:
    # 'ahad': '1234',
    # 'user2': 'password2',
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in VALID_USERS and VALID_USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ── Helper Functions ──────────────────────────────────────────────────────────

def get_location_identifier(city: str, area_slug: str) -> str:
    """Return the Rightmove locationIdentifier for city + area_slug."""
    if area_slug == 'all':
        return ''
    for zone_data in CITY_AREAS.get(city, {}).get('zones', {}).values():
        area_list = zone_data if isinstance(zone_data, list) else zone_data.get('areas', [])
        for area in area_list:
            if not isinstance(area, dict):
                continue
            if area.get('url_slug') == area_slug or area.get('id') == area_slug:
                rid = area.get('region_id', '')
                if rid:
                    return f"REGION^{rid}"
    return ''

def get_area_name(city: str, area_slug: str) -> str:
    """Return the human-readable name for an area slug."""
    if area_slug == 'all':
        return f"All {city.capitalize()}"
    for zone_data in CITY_AREAS.get(city, {}).get('zones', {}).values():
        areas_list = zone_data if isinstance(zone_data, list) else zone_data.get('areas', [])
        for area in areas_list:
            if not isinstance(area, dict):
                continue
            if area.get('url_slug') == area_slug or area.get('id') == area_slug:
                return area.get('name', area_slug)
    clean = area_slug
    for suffix in ['-london-borough', '-royal-borough', '-greater-manchester',
                   '-west-yorkshire', '-west-midlands']:
        clean = clean.replace(suffix, '')
    return clean.replace('-', ' ').title()

def build_filtered_url(city: str, area_slug: str, filter_set: dict,
                        location_identifier: str = '') -> str:
    """Build a Rightmove search URL from filter dict."""
    import urllib.parse
    
    min_price = filter_set.get('min_price')
    max_price = filter_set.get('max_price')
    bedrooms = filter_set.get('bedrooms', 'any')
    max_bedrooms = filter_set.get('max_bedrooms', 'any')
    furnished = filter_set.get('furnished', [])
    property_types = filter_set.get('property_types', [])
    dont_show = filter_set.get('dont_show', [])

    params = ["sortType=6", "channel=RENT", "transactionType=LETTING"]

    if min_price:
        params.append(f"minPrice={min_price}")
    if max_price:
        params.append(f"maxPrice={max_price}")

    if bedrooms and bedrooms != 'any':
        min_bed_val = 5 if bedrooms == '5+' else bedrooms
        params.append(f"minBedrooms={min_bed_val}")
        if max_bedrooms and max_bedrooms != 'any' and max_bedrooms != bedrooms:
            params.append(f"maxBedrooms={max_bedrooms}")
        else:
            params.append(f"maxBedrooms={min_bed_val}")

    if property_types:
        params.append(f"propertyTypes={','.join(property_types)}")

    if furnished and isinstance(furnished, list):
        params.append(f"furnishTypes={','.join(furnished)}")

    valid_dont_show = {'houseShare', 'retirement', 'student'}
    filtered_dont_show = [v for v in dont_show if v in valid_dont_show]
    if filtered_dont_show:
        params.append(f"dontShow={','.join(filtered_dont_show)}")

    if location_identifier:
        encoded_id = urllib.parse.quote(location_identifier, safe='')
        base = "https://www.rightmove.co.uk/property-to-rent/find.html"
        return f"{base}?useLocationIdentifier=true&locationIdentifier={encoded_id}&" + "&".join(params)

    # Slug-based fallback
    if area_slug and area_slug != 'all':
        slug = area_slug
        for suffix in ['-london-borough', '-royal-borough', '-greater-manchester',
                       '-west-yorkshire', '-west-midlands']:
            slug = slug.replace(suffix, '')
        location = '-'.join(w.capitalize() for w in slug.split('-'))
    else:
        location = city.capitalize()

    base = f"https://www.rightmove.co.uk/property-to-rent/{location}.html"
    return base + "?" + "&".join(params)

def make_filter_label(fs: dict, idx: int) -> str:
    """Build a short human-readable label for a filter set."""
    parts = [f"Filter {idx + 1}"]

    if fs.get('min_price') or fs.get('max_price'):
        lo = f"£{fs['min_price']}" if fs.get('min_price') else '£0'
        hi = f"£{fs['max_price']}" if fs.get('max_price') else 'any'
        parts.append(f"{lo}-{hi}/mo")

    if fs.get('bedrooms', 'any') != 'any':
        hi_bed = fs.get('max_bedrooms', 'any')
        if hi_bed and hi_bed != 'any' and hi_bed != fs['bedrooms']:
            parts.append(f"{fs['bedrooms']}-{hi_bed} beds")
        else:
            parts.append(f"{fs['bedrooms']} bed")

    furn_list = fs.get('furnished', [])
    if isinstance(furn_list, list) and furn_list:
        label_map = {
            'furnished': 'Furnished',
            'partFurnished': 'Part-furnished',
            'unfurnished': 'Unfurnished',
        }
        parts.append('/'.join(label_map.get(f, f) for f in furn_list))

    if fs.get('property_types'):
        parts.append('/'.join(fs['property_types']))

    dont_show = fs.get('dont_show', [])
    if isinstance(dont_show, list) and dont_show:
        dont_label_map = {
            'houseShare': 'No HouseShare',
            'retirement': 'No Retirement',
            'student': 'No Student',
        }
        parts.append('/'.join(dont_label_map.get(d, d) for d in dont_show))

    return ' | '.join(parts)

def _ensure_area_filter(organized: dict, area_name: str, filter_label: str):
    """Ensure nested dict keys exist."""
    organized.setdefault(area_name, {}).setdefault(filter_label, [])

# ── Celery Task ───────────────────────────────────────────────────────────────

@celery.task(bind=True, name='scraper.run_multi_filter_scraper')
def run_multi_filter_scraper(self, city: str, areas: list, filter_sets: list,
                              max_properties_per_area: int, job_id: str):
    """
    Celery task for scraping properties.
    Updates task state with progress information.
    """
    from scraper import RightmoveScraper
    from saver import DataSaver
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Initializing scraper...',
                'progress': 0,
                'total': len(areas) * len(filter_sets) * max_properties_per_area,
                'current_area': None,
                'current_filter': None,
            }
        )

        print(f"\n{'=' * 70}", flush=True)
        print(f"Job ID: {job_id} | City: {city} | Areas: {len(areas)} | Filters: {len(filter_sets)}", flush=True)
        print(f"{'=' * 70}\n", flush=True)

        scraper = RightmoveScraper(headless=True, debug=False)
        organized = {}
        all_properties = []

        # Pre-resolve location identifiers
        location_ids = {}
        for area_slug in areas:
            loc_id = get_location_identifier(city, area_slug)
            location_ids[area_slug] = loc_id

        PAGE_SIZE = 24
        total_properties_scraped = 0

        for fi, fs in enumerate(filter_sets):
            filter_label = make_filter_label(fs, fi)
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': f'Processing filter {fi + 1}/{len(filter_sets)}',
                    'progress': total_properties_scraped,
                    'total': len(areas) * len(filter_sets) * max_properties_per_area,
                    'current_filter': f"{filter_label} ({fi + 1}/{len(filter_sets)})",
                    'current_area': None,
                }
            )

            for ai, area_slug in enumerate(areas, 1):
                area_name = get_area_name(city, area_slug)
                loc_id = location_ids.get(area_slug, '')
                
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'Scraping {area_name}',
                        'progress': total_properties_scraped,
                        'total': len(areas) * len(filter_sets) * max_properties_per_area,
                        'current_filter': f"{filter_label} ({fi + 1}/{len(filter_sets)})",
                        'current_area': f"{area_name} ({ai}/{len(areas)})",
                    }
                )

                base_url = build_filtered_url(city, area_slug, fs, loc_id)

                # Paginate through results
                property_urls = []
                page_index = 0

                while len(property_urls) < max_properties_per_area:
                    paginated_url = f"{base_url}&index={page_index}" if page_index > 0 else base_url
                    page_source = scraper.browser.get_page(paginated_url)
                    
                    if not page_source:
                        break

                    page_urls = scraper.extractor.extract_listing_urls(page_source)
                    if not page_urls:
                        break

                    new_urls = [u for u in page_urls if u not in property_urls]
                    if not new_urls:
                        break

                    property_urls.extend(new_urls)

                    if len(page_urls) < PAGE_SIZE:
                        break

                    page_index += PAGE_SIZE

                property_urls = property_urls[:max_properties_per_area]
                _ensure_area_filter(organized, area_name, filter_label)

                area_filter_props = []
                for pi, prop_url in enumerate(property_urls, 1):
                    prop = scraper.scrape_property(prop_url)
                    if prop:
                        prop['search_area'] = area_name
                        prop['search_city'] = city.capitalize()
                        prop['filter_label'] = filter_label
                        area_filter_props.append(prop)
                        all_properties.append(prop)
                        total_properties_scraped += 1
                        
                        # Update progress every 5 properties
                        if total_properties_scraped % 5 == 0:
                            self.update_state(
                                state='PROGRESS',
                                meta={
                                    'status': f'Scraped {total_properties_scraped} properties',
                                    'progress': total_properties_scraped,
                                    'total': len(areas) * len(filter_sets) * max_properties_per_area,
                                    'current_filter': f"{filter_label} ({fi + 1}/{len(filter_sets)})",
                                    'current_area': f"{area_name} ({ai}/{len(areas)})",
                                }
                            )

                organized[area_name][filter_label] = area_filter_props

        scraper.close()

        # Save results
        if all_properties:
            os.makedirs('downloads', exist_ok=True)
            json_file = f'downloads/{job_id}.json'
            excel_file = f'downloads/{job_id}.xlsx'
            
            DataSaver.save_to_json(all_properties, json_file.replace('.json', ''))
            DataSaver.save_organized_excel(organized, excel_file)
            
            return {
                'status': 'SUCCESS',
                'total_properties': len(all_properties),
                'json_file': json_file,
                'excel_file': excel_file,
                'results': all_properties,
            }
        else:
            return {
                'status': 'NO_RESULTS',
                'error': 'No properties found. Try broader filters.',
            }

    except Exception as e:
        print(f"Task error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return {
            'status': 'ERROR',
            'error': str(e),
        }

# ── Flask Routes ──────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    return render_template('index.html', cities=CITIES, city_areas=CITY_AREAS, username=session.get('username'))

@app.route('/start_scraping', methods=['POST'])
@login_required
def start_scraping():
    data = request.json
    city = data.get('city')
    areas = data.get('areas', [])
    filter_sets = data.get('filter_sets', [])
    max_props = data.get('max_properties', 50)

    if not city or not areas:
        return jsonify({'success': False, 'error': 'Missing city or areas'})
    if not filter_sets:
        return jsonify({'success': False, 'error': 'Please add at least one filter set'})

    # Generate unique job ID
    job_id = f"{session.get('username', 'user')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
    
    # Store job ID in session
    if 'jobs' not in session:
        session['jobs'] = []
    session['jobs'].append(job_id)
    session.modified = True

    print(f"\n🚀 New job: {job_id} | city={city} | areas={areas} | filters={len(filter_sets)}", flush=True)

    # Start Celery task
    task = run_multi_filter_scraper.apply_async(
        args=[city, areas, filter_sets, max_props, job_id],
        task_id=job_id
    )

    return jsonify({'success': True, 'job_id': job_id})

@app.route('/status')
@login_required
def status():
    """Get status of the current user's most recent job."""
    job_id = request.args.get('job_id')
    
    if not job_id:
        # Get most recent job from session
        jobs = session.get('jobs', [])
        if not jobs:
            return jsonify({'error': 'No active jobs'})
        job_id = jobs[-1]

    task = AsyncResult(job_id, app=celery)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'running': True,
            'progress': 0,
            'total': 0,
            'status': 'Waiting to start...',
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'running': True,
            'progress': task.info.get('progress', 0),
            'total': task.info.get('total', 0),
            'status': task.info.get('status', ''),
            'current_area': task.info.get('current_area'),
            'current_filter': task.info.get('current_filter'),
        }
    elif task.state == 'SUCCESS':
        result = task.result
        response = {
            'state': task.state,
            'running': False,
            'status': result.get('status'),
            'results': result.get('results', []),
            'json_file': result.get('json_file'),
            'excel_file': result.get('excel_file'),
            'error': result.get('error'),
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'running': False,
            'error': str(task.info),
        }
    else:
        response = {
            'state': task.state,
            'running': False,
            'status': 'Unknown state',
        }

    return jsonify(response)

@app.route('/cancel_job', methods=['POST'])
@login_required
def cancel_job():
    """Cancel a running or queued job."""
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({'success': False, 'error': 'No job_id provided'})
    
    try:
        # Revoke the task
        celery.control.revoke(job_id, terminate=True)
        
        # Delete task result from Redis
        task = AsyncResult(job_id, app=celery)
        task.forget()
        
        # Try to delete files if they exist
        for ext in ['json', 'xlsx']:
            file_path = f'downloads/{job_id}.{ext}'
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        print(f"✅ Cancelled job: {job_id}", flush=True)
        return jsonify({'success': True, 'message': 'Job cancelled successfully'})
        
    except Exception as e:
        print(f"❌ Cancel error: {e}", flush=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<file_type>')
@login_required
def download(file_type):
    job_id = request.args.get('job_id')
    
    if not job_id:
        jobs = session.get('jobs', [])
        if not jobs:
            return "No job ID provided", 404
        job_id = jobs[-1]

    file_ext = 'json' if file_type == 'json' else 'xlsx'
    file_path = f'downloads/{job_id}.{file_ext}'
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ── Startup: Clear Redis Queue ────────────────────────────────────────────────

def clear_queue_on_startup():
    """Clear all pending tasks from Redis on server startup."""
    try:
        # Purge the default queue
        celery.control.purge()
        
        # Clear task results
        import redis
        r = redis.Redis.from_url(app.config['CELERY_RESULT_BACKEND'])
        
        # Delete all celery task metadata
        for key in r.scan_iter("celery-task-meta-*"):
            r.delete(key)
        
        print("=" * 70)
        print("✅ STARTUP: Cleared all pending tasks from queue")
        print("=" * 70)
    except Exception as e:
        print(f"⚠️  Warning: Could not clear queue on startup: {e}")

# Call on startup
clear_queue_on_startup()

if __name__ == '__main__':
    os.makedirs('downloads', exist_ok=True)
    print("=" * 70)
    print("⚠️  WARNING: This is the production app!")
    print("   Use 'gunicorn' or 'waitress-serve' to run, not 'python app.py'")
    print("=" * 70)
    app.run(debug=False, host='0.0.0.0', port=5000)