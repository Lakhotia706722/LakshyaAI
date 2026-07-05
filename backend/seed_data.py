"""
Seed script — populates the database with demo data.
Phase 6: creates a demo organization and assigns the admin user as owner.
"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal, engine
from app.models import (
    Base, User, Organization, OrgMember, OrgRole,
    Company, Deal, DealStage,
)
from app.routers.auth import hash_password


def seed_data():
    """Seed the database with demo data."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping...")
            return

        print("Seeding demo organization and admin user...")

        # Create demo org
        org = Organization(
            name="Lakshya Demo Org",
            plan_tier="free",
        )
        db.add(org)
        db.flush()

        # Create admin user (bcrypt-hashed)
        admin_user = User(
            email="admin@lakshya.ai",
            password_hash=hash_password("admin123"),
            name="Admin User",
            is_email_verified=True,   # pre-verified for demo
        )
        db.add(admin_user)
        db.flush()

        # Link user as owner
        membership = OrgMember(org_id=org.id, user_id=admin_user.id, role=OrgRole.OWNER)
        db.add(membership)
        db.commit()

        print("Seeding companies...")
        company_data = [
            ("TechVision Solutions", "SaaS", "Bangalore", "Karnataka", "50-200", ["Python", "React", "AWS"]),
            ("Mehta Manufacturing Ltd", "Manufacturing", "Pune", "Maharashtra", "200-500", ["ERP", "IoT"]),
            ("Digital Finance Corp", "BFSI", "Mumbai", "Maharashtra", "100-250", ["Java", "Oracle", "Blockchain"]),
            ("Sharma Textiles Pvt Ltd", "Textile", "Surat", "Gujarat", "500-1000", ["ERP", "CRM"]),
            ("CloudMinds Technologies", "SaaS", "Hyderabad", "Telangana", "20-50", ["NodeJS", "MongoDB", "React"]),
            ("AgriTech Innovations", "Agriculture", "Jaipur", "Rajasthan", "10-50", ["IoT", "Mobile Apps"]),
            ("HealthPlus Diagnostics", "Healthcare", "Chennai", "Tamil Nadu", "100-200", ["EMR", "Cloud"]),
            ("EduLearn Platform", "EdTech", "Bangalore", "Karnataka", "30-100", ["React", "Python", "AI"]),
            ("LogiMove Solutions", "Logistics", "Delhi", "Delhi", "150-300", ["GPS", "Mobile", "ERP"]),
            ("RetailHub Systems", "Retail", "Ahmedabad", "Gujarat", "50-150", ["POS", "CRM", "Analytics"]),
            ("FinServe NBFC", "BFSI", "Mumbai", "Maharashtra", "200-400", ["Core Banking", "Java"]),
            ("GreenEnergy Corp", "Energy", "Pune", "Maharashtra", "100-200", ["IoT", "Analytics"]),
            ("AutoParts India", "Automotive", "Gurgaon", "Haryana", "300-500", ["ERP", "Supply Chain"]),
            ("MediaWorks Digital", "Media", "Mumbai", "Maharashtra", "50-100", ["CMS", "Streaming"]),
            ("ConsultPro Services", "Consulting", "Bangalore", "Karnataka", "20-50", ["Salesforce", "SAP"]),
        ]

        companies = []
        for name, industry, city, state, emp_band, tech_stack in company_data:
            company = Company(
                org_id=org.id,
                name=name,
                industry=industry,
                city=city,
                state=state,
                employee_band=emp_band,
                gst_number=f"29{random.randint(10000000000, 99999999999)}",
                udyam_number=f"UDYAM-{state[:2].upper()}-{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
                financial_health_score=random.randint(45, 95),
                growth_signal=random.randint(30, 90),
                tech_stack_tags=tech_stack,
                source="seed_data",
            )
            companies.append(company)
            db.add(company)

        db.commit()
        print(f"Created {len(companies)} companies")

        for company in companies:
            db.refresh(company)

        print("Seeding deals...")
        deal_templates = [
            "Annual License Renewal",
            "Q4 Expansion Deal",
            "New Implementation",
            "Platform Upgrade",
            "Multi-Year Contract",
            "Enterprise Package",
            "Starter Plan",
            "Professional Services",
        ]
        owners = ["Rajesh Kumar", "Priya Sharma", "Amit Patel", "Neha Reddy", "Vikram Singh"]
        stages = list(DealStage)

        for _ in range(20):
            company = random.choice(companies)
            stage = random.choice(stages)
            if "10-50" in company.employee_band:
                value = random.randint(200000, 1000000)
            elif "50-200" in company.employee_band:
                value = random.randint(500000, 2500000)
            else:
                value = random.randint(1000000, 10000000)

            deal = Deal(
                org_id=org.id,
                company_id=company.id,
                title=f"{random.choice(deal_templates)} - {company.name}",
                stage=stage,
                value_inr=value,
                owner_name=random.choice(owners),
                sentiment_trend=[],
                risk_flag=random.random() < 0.15,
                risk_reason="Long silence period" if random.random() < 0.5 else "Price objection detected",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            )
            db.add(deal)

        db.commit()
        print("Created 20 deals")
        print("\n✅ Database seeded successfully!")
        print("\nDemo login:")
        print("  Email:    admin@lakshya.ai")
        print("  Password: admin123")
        print("  Org:      Lakshya Demo Org")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
