"""
Django management command to sync fixtures from FA Fulltime subscriptions.
Can be run as a scheduled job (e.g., every 3 hours) to keep fixtures up to date.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from content.models import Match, FullTimeSubscription
from content.sources.fulltime import fetch_via_proxy, parse_fixtures_html
import logging

logger = logging.getLogger(__name__)

# Cloudflare Worker proxy configuration
PROXY_BASE = "https://your-worker.workers.dev"  # Set to your actual Worker URL


class Command(BaseCommand):
    help = "Re-sync fixtures/results from FA Full-Time pages"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be synced without making changes',
        )
        parser.add_argument(
            '--club-id',
            type=int,
            help='Sync only for a specific club ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        club_id = options.get('club_id')
        
        # Get active subscriptions
        subs = FullTimeSubscription.objects.filter(is_active=True)
        if club_id:
            subs = subs.filter(club_id=club_id)
        
        if not subs.exists():
            self.stdout.write(self.style.WARNING("No active FA Fulltime subscriptions found"))
            return
        
        total_updates = 0
        total_created = 0
        total_updated = 0
        
        for sub in subs:
            try:
                self.stdout.write(f"Syncing {sub.club.name} - {sub.team_display_name}")
                
                if dry_run:
                    self.stdout.write(f"  [DRY RUN] Would fetch: {sub.competition_url}")
                    continue
                
                # Fetch HTML via proxy
                html = fetch_via_proxy(PROXY_BASE, sub.competition_url)
                
                # Parse fixtures
                items = parse_fixtures_html(html, sub.team_display_name)
                
                if not items:
                    self.stdout.write(self.style.WARNING(f"  No fixtures found for {sub.club.name}"))
                    continue
                
                # Group by fixture key for upsert
                by_key = {i["fixture_key"]: i for i in items}
                
                # Upsert fixtures
                for key, fixture_data in by_key.items():
                    match_data = {
                        "source": "fulltime_html",
                        "source_competition_url": sub.competition_url,
                        "competition": fixture_data["competition"],
                        "round_name": fixture_data["round_name"],
                        "home_team": fixture_data["home_team"],
                        "away_team": fixture_data["away_team"],
                        "home_away": "HOME" if fixture_data["home_away"] == "H" else "AWAY",
                        "opponent": fixture_data["opponent_name"],
                        "date": fixture_data["kickoff_utc"],
                        "kickoff_utc": fixture_data["kickoff_utc"],
                        "kickoff_local_tz": fixture_data["kickoff_local_tz"],
                        "venue": fixture_data["venue"],
                        "status": fixture_data["status"],
                        "raw_payload": fixture_data["raw"],
                        "last_synced_at": timezone.now(),
                    }
                    
                    match, is_created = Match.objects.update_or_create(
                        club=sub.club,
                        fixture_key=key,
                        defaults=match_data
                    )
                    
                    if is_created:
                        total_created += 1
                        self.stdout.write(f"  Created: {fixture_data['home_team']} vs {fixture_data['away_team']}")
                    else:
                        total_updated += 1
                        self.stdout.write(f"  Updated: {fixture_data['home_team']} vs {fixture_data['away_team']}")
                    
                    total_updates += 1
                
                self.stdout.write(self.style.SUCCESS(f"  Synced {len(by_key)} fixtures for {sub.club.name}"))
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Failed to sync {sub.club.name}: {str(e)}")
                )
                logger.error(f"Sync failed for {sub.club.name}: {str(e)}", exc_info=True)
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY RUN] Would sync {subs.count()} subscriptions"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync completed: {total_created} created, {total_updated} updated, {total_updates} total"
                )
            )
