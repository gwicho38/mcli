#!/usr/bin/env python3
"""
Debug script to explore the UK Parliament API structure
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json

import aiohttp


async def explore_uk_api():
    """Explore the UK Parliament API to understand its structure"""
    print("🔍 Exploring UK Parliament API Structure")
    print("=" * 50)

    base_url = "https://interests-api.parliament.uk/api/v1"
    categories = []

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        },
    ) as session:
        try:
            # Check categories
            print("\n📋 Available Categories:")
            categories_url = f"{base_url}/Categories"
            async with session.get(categories_url, params={"Take": 100}) as response:
                print(f"Categories response status: {response.status}")

                if response.status == 200:
                    response_text = await response.text()
                    print(f"Response text length: {len(response_text)}")
                    print(f"First 500 chars: {response_text[:500]}")
                    try:
                        import json

                        data = json.loads(response_text)
                        print(
                            f"JSON keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                        )
                        categories = data.get("items", [])
                        print(f"Found {len(categories)} categories:")
                        for cat in categories[:10]:  # Show first 10
                            print(
                                f"  - {cat.get('name', 'No name')} (ID: {cat.get('id', 'No ID')})"
                            )
                    except Exception as e:
                        print(f"Failed to parse JSON: {e}")
                        print(f"Raw response: {response_text}")
                else:
                    response_text = await response.text()
                    print(f"Failed to fetch categories: HTTP {response.status}")
                    print(f"Response text: {response_text[:500]}")
                    return

            # Try to get some sample interests if we have categories
            if categories:
                # Look for Shareholdings category specifically
                shareholdings_cat = None
                for cat in categories:
                    if "shareholding" in cat.get("name", "").lower():
                        shareholdings_cat = cat
                        break

                target_cat = shareholdings_cat or categories[0]
                print(f"\n📄 Sample Interests from category '{target_cat.get('name')}':")
                first_cat = target_cat
                interests_url = f"{base_url}/Interests"
                params = {"categoryId": first_cat.get("id"), "Take": 3}
                async with session.get(interests_url, params=params) as response:
                    print(f"Interests response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        interests = data.get("items", [])
                        print(
                            f"Found {len(interests)} interests in category '{first_cat.get('name')}':"
                        )
                        for i, interest in enumerate(interests):
                            print(f"  Interest {i+1} raw data keys: {list(interest.keys())}")
                            print(f"    Member ID: {interest.get('memberId')}")
                            print(f"    Description: {interest.get('description', '')[:100]}")
                            print(
                                f"    Date: {interest.get('registeredLate') or interest.get('dateCreated')}"
                            )
                            if i == 0:  # Show full data for first interest
                                print(f"    Full data: {interest}")
                            print()
                    else:
                        response_text = await response.text()
                        print(f"Failed to fetch interests: HTTP {response.status}")
                        print(f"Response: {response_text[:200]}")

                # Try to get member info using a sample member ID
                if categories:
                    print(f"\n👤 Testing Member API:")
                    interests_url = f"{base_url}/Interests"
                    params = {"categoryId": first_cat.get("id"), "Take": 1}
                    async with session.get(interests_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            interests = data.get("items", [])
                            if interests:
                                member_id = interests[0].get("memberId")
                                if member_id:
                                    member_url = f"{base_url}/Members/{member_id}"
                                    async with session.get(member_url) as member_response:
                                        print(
                                            f"Member API response status: {member_response.status}"
                                        )
                                        if member_response.status == 200:
                                            member_data = await member_response.json()
                                            print(f"Successfully fetched member {member_id}:")
                                            print(f"  Available fields: {list(member_data.keys())}")
                                            for key in [
                                                "name",
                                                "displayAs",
                                                "nameGiven",
                                                "nameFull",
                                                "nameFamily",
                                            ]:
                                                if key in member_data:
                                                    print(f"    {key}: {member_data[key]}")
                                        else:
                                            response_text = await member_response.text()
                                            print(
                                                f"Failed to fetch member {member_id}: HTTP {member_response.status}"
                                            )
                                            print(f"Response: {response_text[:200]}")

        except Exception as e:
            print(f"❌ API exploration failed: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(explore_uk_api())
