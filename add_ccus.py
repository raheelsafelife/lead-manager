"""
Script to add CCUs extracted from the images provided by the user.
Run this script once to populate the CCUs table.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app import crud_ccus

# CCU data extracted from the images
ccus_data = [
    {
        "name": "DuPage County CS Programs",
        "phone": "(630)407-6500",
        "address": "421 N. County Farm Rd., Wheaton, IL 60187",
        "email": "csprograms@dupagecounty.gov"
    },
    {
        "name": "Grundy County Health Department",
        "phone": "(815)941-3400",
        "address": "1320 Union St., Morris, IL 60450",
        "email": None
    },
    {
        "name": "Senior Services Ass. Elgin",
        "phone": "(847)741-0404",
        "address": "101 S. Grove Ave., Elgin, IL 60120",
        "email": "ssaiccu@seniorservicesassoc.org"
    },
    {
        "name": "Senior Services Ass. Aurora",
        "phone": "(630)897-4035",
        "address": "2111 Plum St. Suite 250, Aurora, IL 60506",
        "email": "ssaiccu@seniorservicesassoc.org"
    },
    {
        "name": "Catholic Charities Of the Diocese of Joliet (Kankakee)",
        "phone": "(815)932-1921",
        "address": "249 S. Schuyler Ave. #300, Kankakee, IL 60901",
        "email": None
    },
    {
        "name": "Senior Services Ass. Kendall",
        "phone": "(630)553-5777",
        "address": "908 Game Farm Rd., Yorkville, IL 60560",
        "email": "ssaiccu@seniorservicesassoc.org"
    },
    {
        "name": "Senior Services of Will County",
        "phone": "(815)740-4225",
        "address": "251 N Center St., Joliet, IL 60435",
        "email": "ccuwillco@willcountyseniors.org"
    },
    {
        "name": "Lake County Senior Social Services (Lake)",
        "phone": "(847)546-5733",
        "address": "116 N Lincoln Ave. Round Lake, IL 60073",
        "email": "cclakeccu@catholiccharities.net"
    },
    {
        "name": "Catholic Charities NWSS",
        "phone": "(847)253-5500",
        "address": "1801 W. Central Rd., Arlington Heights, IL 60005",
        "email": "infoccnw@catholiccharities.net"
    },
    {
        "name": "Catholic Charities SSSS",
        "phone": "(708)596-2222",
        "address": "15300 S. Lexington Ave., Harvey, IL 60426",
        "email": "ccssssccu@catholiccharities.net"
    },
    {
        "name": "CCSI Case Coordination, LLC (Area 5)",
        "phone": "(312)726-1364",
        "address": "329 W 18th St. Suite 801, Chicago, IL 60616",
        "email": "chicagoccu@ccsiccu.com"
    },
    {
        "name": "Catholic Charities SWSS",
        "phone": "(773)349-8092",
        "address": "2601 W. Marquette Ave, Chicago, IL 60629",
        "email": "intakesubarea7@catholiccharities"
    },
    {
        "name": "Premier Home Health Care (North)",
        "phone": "(312)766-3361",
        "address": "6321 N. Avondale Suite 101A, Chicago, IL 60631",
        "email": "premierccunorth@phhc.com"
    },
    {
        "name": "Premier Home Health Care (South)",
        "phone": "(312)256-2900",
        "address": "1081 S. Western Ave Suite LL 100, Chicago, IL 60643",
        "email": "PremierILCCU@phss.com"
    },
    {
        "name": "Catholic Charities OAS/NENW",
        "phone": "(773)583-9224",
        "address": "3125 N. Knox, Chicago, IL 60641",
        "email": "ccnenwccu@catholiccharities.net"
    },
    {
        "name": "CCSI Case Coordination, LLC (Area 6)",
        "phone": "(773)341-1790",
        "address": "310 S. Racine 8N, Chicago, IL 60607",
        "email": "chicagoccu@ccsiccu.com"
    },
    {
        "name": "CCSI Case Coordination, LLC (Area 10)",
        "phone": "(773)341-1790",
        "address": "310 S. Racine 8N, Chicago, IL 60607",
        "email": "ccsiarea10@ccsiccu.com"
    },
    {
        "name": "CCSI Case Coordination, LLC (Area 8)",
        "phone": "(312)686-1515",
        "address": "1000 E. 111th St. Suite 800, Chicago, IL 60628",
        "email": "ccsisoutheast@ccsiccu.com"
    },
    {
        "name": "CCSI Case Coordination, LLC (Area 11)",
        "phone": "(312)686-1515",
        "address": "1000 E. 111th St. Suite 800, Chicago, IL 60628",
        "email": "ccsisoutheast@ccsiccu.com"
    },
    {
        "name": "CCSI Case Coordination, LLC (Area 12)",
        "phone": "(312)686-1515",
        "address": "1000 E. 111th St. Suite 800, Chicago, IL 60628",
        "email": "ccsisoutheast@ccsiccu.com"
    },
    {
        "name": "Solutions for Care",
        "phone": "(708)447-2448",
        "address": "7222 W. Cermak Rd. Suite 200, Riverside, IL 60546",
        "email": "Info@solutionsforcare.org"
    },
    {
        "name": "Aging Care Connections",
        "phone": "(708)354-1323",
        "address": "111 W Harris Ave, La Grange, IL 60525",
        "email": "Info@agingcareconnection.org"
    },
    {
        "name": "Oak Park Township",
        "phone": "(708)383-8060",
        "address": "130 S. Oak Park Ave, 2nd Floor, Oak Park, IL 60302",
        "email": "ccureferrals@oakparktownship.org"
    },
    {
        "name": "Pathlights",
        "phone": "(708)361-0219",
        "address": "7808 West College Drive Suite 5E, Palos Heights, IL 60463",
        "email": "ldoa.tx@pathlights.org"
    },
    {
        "name": "Kenneth Young Center (Schaumburg)",
        "phone": "(847)524-8800",
        "address": "1001 Rohlwing Rd., Elk Grove Village, IL 60007",
        "email": None
    },
    {
        "name": "North Shore Senior Center",
        "phone": "(847)784-6040",
        "address": "161 Northfield Rd, IL 60061",
        "email": "mco@nssc.org"
    },
    {
        "name": "Stickney Township Office on Aging",
        "phone": "(708)636-8850",
        "address": "7745 S. Leamington Ave., Burbank, IL 60459",
        "email": "klivigni@townshipofstickney.org"
    },
]


def main():
    db = SessionLocal()
    
    created_count = 0
    skipped_count = 0
    
    print("=" * 60)
    print("Adding CCUs to the database...")
    print("=" * 60)
    
    for ccu_data in ccus_data:
        # Check if CCU already exists
        existing = crud_ccus.get_ccu_by_name(db, ccu_data["name"])
        
        if existing:
            print(f"⏭️  SKIPPED (already exists): {ccu_data['name']}")
            skipped_count += 1
        else:
            # Create the CCU
            ccu = crud_ccus.create_ccu(
                db=db,
                name=ccu_data["name"],
                created_by="system",
                created_by_id=1,  # System user
                address=ccu_data.get("address"),
                phone=ccu_data.get("phone"),
                fax=ccu_data.get("fax"),
                email=ccu_data.get("email"),
                care_coordinator_name=ccu_data.get("care_coordinator_name")
            )
            print(f"✅ CREATED: {ccu.name}")
            created_count += 1
    
    db.close()
    
    print("=" * 60)
    print(f"Summary: {created_count} created, {skipped_count} skipped")
    print("=" * 60)


if __name__ == "__main__":
    main()
