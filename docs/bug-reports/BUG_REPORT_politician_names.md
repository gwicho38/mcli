# Bug Report: Real Politician Names Not Being Stored in Database

## Issue Summary
Enhanced scrapers are successfully extracting real politician names (Greg Abbott, Kathy Hochul, Ron DeSantis, etc.) but the workflow is storing generic placeholder names ("Texas State Official", "Florida State Official") instead of the actual politician names in the database.

## Expected Behavior
When scrapers extract real politician names like:
- "Greg Abbott" (Texas Governor)
- "Kathy Hochul" (New York Governor) 
- "Ron DeSantis" (Florida Governor)
- "J.B. Pritzker" (Illinois Governor)

These names should be stored in the `politicians` table and displayed in the disclosure tables.

## Actual Behavior
Database contains generic entries like:
- "Texas State Official (texas_ethics_commission)"
- "Florida State Official (florida_ethics_commission)" 
- "New York State Official (new_york_jcope)"

## Evidence

### 1. Scrapers Working Correctly
Test output shows real names being extracted:
```
🧪 Testing Enhanced US States Scrapers
  1. Greg Abbott (Texas)
  2. Dan Patrick (Texas) 
  3. Kathy Hochul (New York)
  4. Ron DeSantis (Florida)
  5. J.B. Pritzker (Illinois)
✅ SUCCESS: Enhanced US states scrapers are extracting politician names!
```

### 2. Database Contains Wrong Names
```bash
mcli workflow politician-trading politicians --limit 10
```
Shows:
- "Texas State Official (texas_ethics_commission)"
- "Florida State Official (florida_ethics_commission)"
- "New York State Official (new_york_jcope)"

### 3. Table Display Shows Placeholders
```bash
mcli workflow politician-trading disclosures --limit 5
```
Shows:
- "Florida State Official (florida_eth..."
- "New York State Official (new_york_j..."

## Root Cause Analysis

### Code Investigation
1. **workflow.py:196** - Correctly extracts `politician_name` from `raw_data`:
   ```python
   politician_name = disclosure.raw_data.get("politician_name", "")
   ```

2. **PoliticianMatcher.find_politician()** - Only returns matches for existing politicians:
   ```python
   def find_politician(self, name: str, bioguide_id: str = None) -> Optional[Politician]:
       # Returns None if politician not found in existing database
   ```

3. **workflow.py:210-213** - Skips disclosure when no politician match found:
   ```python
   if not politician:
       logger.warning(f"No politician match for: {politician_name}")
       job.records_failed += 1
       continue
   ```

### The Problem
When the workflow processes a disclosure with `politician_name = "Greg Abbott"`:
1. `PoliticianMatcher.find_politician("Greg Abbott")` returns `None` (not in existing DB)
2. Workflow skips the disclosure as "failed"
3. Later, generic placeholder politicians get created instead of using the real names

## Files Involved
- `/src/mcli/workflow/politician_trading/workflow.py` - Main processing logic
- `/src/mcli/workflow/politician_trading/scrapers.py` - PoliticianMatcher class
- `/src/mcli/workflow/politician_trading/scrapers_us_states.py` - Enhanced scrapers with real names
- `/src/mcli/workflow/politician_trading/commands.py` - Table display (already fixed)

## Impact
- ✅ Scrapers extract real names correctly
- ✅ Table formatting works properly (35 char limit, min_width=25)
- ❌ Database stores placeholder names instead of real names
- ❌ Users see generic "State Official" instead of actual politician names

## Next Steps
1. Investigate politician creation logic for when no match is found
2. Modify workflow to create new politician records using real names from `raw_data`
3. Test that real names appear in database and table displays
4. Verify existing data integrity is maintained

## Priority
**High** - This defeats the purpose of the enhanced scrapers and provides poor user experience.

## Labels
- bug
- workflow
- database  
- politician-matching
- data-quality