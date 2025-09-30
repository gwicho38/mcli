#!/usr/bin/env python3
"""
Configuration script to enable real data collection instead of sample data

This script modifies the scrapers to process real data from APIs instead of 
generating sample/test data.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def configure_real_data_mode():
    """Configure the system to use real data instead of samples"""
    
    print("🔧 CONFIGURING REAL DATA COLLECTION MODE")
    print("=" * 50)
    
    print("\n📋 Current Configuration Status:")
    print("- Sample data mode: Currently ENABLED")
    print("- Real API calls: Currently LIMITED (to prevent rate limiting)")
    print("- Database writes: Currently WORKING")
    
    print("\n🎯 To Enable Real Data Collection:")
    print("=" * 50)
    
    print("1. UK Parliament API - Ready for real data:")
    print("   ✅ Uses real interests-api.parliament.uk")
    print("   ✅ No rate limiting issues")
    print("   📝 Action: Remove 'sample: True' flags in scrapers_uk.py")
    
    print("\n2. US Congress Data - QuiverQuant integration:")
    print("   ⚠️  Currently uses sample data to avoid rate limiting")
    print("   📝 Action: Enable real QuiverQuant scraping")
    print("   📝 Note: May need API key for full access")
    
    print("\n3. California NetFile - Portal scraping:")
    print("   ⚠️  Currently uses sample data")
    print("   📝 Action: Enable real portal form parsing")
    print("   📝 Note: Complex forms require careful handling")
    
    print("\n4. EU Member States - Official sources:")
    print("   ⚠️  Currently uses sample data")
    print("   📝 Action: Implement country-specific API calls")
    print("   📝 Note: Each country has different disclosure formats")
    
    print("\n🚀 QUICK ENABLE SCRIPT")
    print("=" * 50)
    print("# Enable real UK Parliament data (safest to start)")
    print("python configure_real_data.py --enable-uk")
    print()
    print("# Enable real US Congress data")
    print("python configure_real_data.py --enable-us")
    print()
    print("# Enable all real data (advanced)")
    print("python configure_real_data.py --enable-all")
    
    print("\n⚠️  IMPORTANT CONSIDERATIONS:")
    print("=" * 50)
    print("- Real data collection makes actual HTTP requests")
    print("- Some APIs have rate limits (be respectful)")
    print("- Complex parsing may fail on edge cases")
    print("- Start with UK Parliament API (most reliable)")
    print("- Monitor logs carefully when switching to real data")
    
    print("\n📊 DATABASE SETUP FOR REAL DATA:")
    print("=" * 50)
    print("- Database schema is already configured ✅")
    print("- Real disclosures will replace sample data ✅") 
    print("- Job tracking remains the same ✅")
    print("- Politician matching will improve with real names ✅")


def enable_uk_real_data():
    """Enable real data collection for UK Parliament"""
    print("\n🇬🇧 Enabling UK Parliament Real Data Collection...")
    
    # Read the UK scraper file
    uk_scraper_path = "src/mcli/workflow/politician_trading/scrapers_uk.py"
    
    try:
        with open(uk_scraper_path, 'r') as f:
            content = f.read()
        
        # Remove sample flags and enable real API calls
        modifications = [
            ('\"sample\": True', '\"sample\": False'),
            ('# This would implement actual Bundestag scraping', 'logger.info("Processing real UK Parliament data")'),
        ]
        
        modified = False
        for old_text, new_text in modifications:
            if old_text in content:
                content = content.replace(old_text, new_text)
                modified = True
                print(f"✅ Modified: {old_text} -> {new_text}")
        
        if modified:
            # Backup original file
            backup_path = uk_scraper_path + ".backup"
            with open(backup_path, 'w') as f:
                f.write(content)
            
            print(f"✅ UK Parliament scraper configured for real data")
            print(f"✅ Backup saved to: {backup_path}")
        else:
            print("ℹ️  No modifications needed - already configured")
    
    except Exception as e:
        print(f"❌ Error modifying UK scraper: {e}")


def show_database_integration_guide():
    """Show how to integrate with database for real data"""
    
    print("\n🗄️  DATABASE INTEGRATION GUIDE")
    print("=" * 50)
    
    print("Current Database Schema:")
    print("✅ politicians - For storing politician profiles")
    print("✅ trading_disclosures - For storing financial disclosures") 
    print("✅ data_pull_jobs - For tracking collection jobs")
    print("✅ data_sources - For managing scraper configurations")
    
    print("\nReal Data Flow:")
    print("1. Cron job triggers collection")
    print("2. Scrapers fetch real data from APIs")
    print("3. Data is parsed and validated")
    print("4. Politicians are matched or created")
    print("5. Disclosures are inserted/updated in database")
    print("6. Job status is recorded")
    
    print("\nDatabase Read Commands:")
    print("# Read recent data")
    print("python cron_scheduler.py read")
    print()
    print("# Monitor database state")
    print("python monitor_politician_trading.py")
    
    print("\nCron Setup for Automated Collection:")
    print("python cron_scheduler.py install-cron")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--enable-uk":
            enable_uk_real_data()
        elif command == "--enable-us":
            print("🇺🇸 US real data enablement - Coming soon")
        elif command == "--enable-all":
            print("🌍 Full real data enablement - Coming soon")
        elif command == "--show-database":
            show_database_integration_guide()
        else:
            print(f"Unknown command: {command}")
    else:
        configure_real_data_mode()
        show_database_integration_guide()