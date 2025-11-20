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
                response_text = await response.text()
                print(f"Response text length: {len(response_text)}")

                if response.status == 200:
                    data = await response.json()
                    categories = data.get("value", [])
                    print(f"Found {len(categories)} categories:")
                    for cat in categories[:10]:  # Show first 10
                        print(f"  - {cat.get('name', 'No name')} (ID: {cat.get('id', 'No ID')})")
                else:
                    print(f"Failed to fetch categories: HTTP {response.status}")
                    print(f"Response text: {response_text[:500]}")

            # Try to get some sample interests
            print(f"\n📄 Sample Interests (first category):")
            if categories:
                first_cat = categories[0]
                interests_url = f"{base_url}/Interests"
                params = {"categoryId": first_cat.get("id"), "Take": 5}
                async with session.get(interests_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        interests = data.get("value", [])
                        print(
                            f"Found {len(interests)} interests in category '{first_cat.get('name')}':"
                        )
                        for interest in interests:
                            print(f"  - Member ID: {interest.get('memberId')}")
                            print(f"    Description: {interest.get('description', '')[:100]}...")
                            print(
                                f"    Date: {interest.get('registeredLate') or interest.get('dateCreated')}"
                            )
                            print()
                    else:
                        print(f"Failed to fetch interests: HTTP {response.status}")

            # Try to get member info
            print(f"\n👤 Testing Member API:")
            if categories and len(categories) > 0:
                # Get a sample interest to get a member ID
                first_cat = categories[0]
                interests_url = f"{base_url}/Interests"
                params = {"categoryId": first_cat.get("id"), "Take": 1}
                async with session.get(interests_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        interests = data.get("value", [])
                        if interests:
                            member_id = interests[0].get("memberId")
                            if member_id:
                                member_url = f"{base_url}/Members/{member_id}"
                                async with session.get(member_url) as member_response:
                                    if member_response.status == 200:
                                        member_data = await member_response.json()
                                        print(f"Successfully fetched member {member_id}:")
                                        print(f"  Name fields: {list(member_data.keys())}")
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
                                        print(
                                            f"Failed to fetch member {member_id}: HTTP {member_response.status}"
                                        )

        except Exception as e:
            print(f"❌ API exploration failed: {e}")


if __name__ == "__main__":
    asyncio.run(explore_uk_api())
