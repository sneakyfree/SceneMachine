"""
Performer seed data for ActForge marketplace.

Creates 50 diverse sample performers with realistic statistics
for development and testing purposes.
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models.performer import (
    Performer,
    PerformerType,
    PerformerAvailability,
    PerformerVerification,
)


# Sample performer data with diverse demographics
SAMPLE_PERFORMERS: list[dict[str, Any]] = [
    # High-tier performers (ACI 90-99)
    {
        "stage_name": "Aurora Blake",
        "bio": "Award-winning dramatic performer with 15 years of theater experience. Specializes in emotional depth and nuanced character portrayal.",
        "specialties": ["dramatic", "romantic", "period"],
        "aci_score": 97.5,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.ELITE,
        "total_bookings": 1250,
        "completed_bookings": 1220,
        "profile_image": "https://randomuser.me/api/portraits/women/1.jpg",
    },
    {
        "stage_name": "Marcus Chen",
        "bio": "Action specialist and martial arts expert. Known for fluid motion capture and intense fight choreography.",
        "specialties": ["action", "martial_arts", "stunts"],
        "aci_score": 96.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.ELITE,
        "total_bookings": 980,
        "completed_bookings": 965,
        "profile_image": "https://randomuser.me/api/portraits/men/2.jpg",
    },
    {
        "stage_name": "Sofia Rodriguez",
        "bio": "Comedic genius with impeccable timing. Brings characters to life with expressive gestures and perfect comedic beats.",
        "specialties": ["comedic", "slapstick", "animation"],
        "aci_score": 95.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.ELITE,
        "total_bookings": 875,
        "completed_bookings": 860,
        "profile_image": "https://randomuser.me/api/portraits/women/3.jpg",
    },
    {
        "stage_name": "James Wright",
        "bio": "Veteran performer specializing in authority figures and executives. Distinguished presence for corporate and dramatic content.",
        "specialties": ["dramatic", "corporate", "authority"],
        "aci_score": 94.1,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.ELITE,
        "total_bookings": 720,
        "completed_bookings": 705,
        "profile_image": "https://randomuser.me/api/portraits/men/4.jpg",
    },
    {
        "stage_name": "Luna Sato",
        "bio": "Horror and thriller specialist. Master of building tension and delivering spine-chilling performances.",
        "specialties": ["horror", "thriller", "dramatic"],
        "aci_score": 93.7,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.ELITE,
        "total_bookings": 650,
        "completed_bookings": 638,
        "profile_image": "https://randomuser.me/api/portraits/women/5.jpg",
    },
    # Mid-high tier performers (ACI 85-89)
    {
        "stage_name": "David Kim",
        "bio": "Versatile performer comfortable in any genre. Quick learner with exceptional adaptability.",
        "specialties": ["dramatic", "comedic", "action"],
        "aci_score": 89.4,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 520,
        "completed_bookings": 495,
        "profile_image": "https://randomuser.me/api/portraits/men/6.jpg",
    },
    {
        "stage_name": "Emma Thompson",
        "bio": "Period drama specialist with classical training. Brings elegance and authenticity to historical pieces.",
        "specialties": ["period", "romantic", "dramatic"],
        "aci_score": 88.9,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 480,
        "completed_bookings": 460,
        "profile_image": "https://randomuser.me/api/portraits/women/7.jpg",
    },
    {
        "stage_name": "Carlos Mendez",
        "bio": "High-energy performer perfect for action and adventure content. Known for athletic motion work.",
        "specialties": ["action", "adventure", "stunts"],
        "aci_score": 88.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 445,
        "completed_bookings": 425,
        "profile_image": "https://randomuser.me/api/portraits/men/8.jpg",
    },
    {
        "stage_name": "Nina Petrova",
        "bio": "Dance and musical performance specialist. Graceful movements for choreographed sequences.",
        "specialties": ["musical", "dance", "romantic"],
        "aci_score": 87.6,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 410,
        "completed_bookings": 390,
        "profile_image": "https://randomuser.me/api/portraits/women/9.jpg",
    },
    {
        "stage_name": "Ryan O'Connor",
        "bio": "Character actor with range from comedic sidekick to serious supporting roles.",
        "specialties": ["comedic", "dramatic", "character"],
        "aci_score": 86.3,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 380,
        "completed_bookings": 358,
        "profile_image": "https://randomuser.me/api/portraits/men/10.jpg",
    },
    {
        "stage_name": "Yuki Tanaka",
        "bio": "Animation and fantasy specialist. Brings otherworldly characters to life with imaginative motion work.",
        "specialties": ["animation", "fantasy", "action"],
        "aci_score": 85.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 350,
        "completed_bookings": 332,
        "profile_image": "https://randomuser.me/api/portraits/women/11.jpg",
    },
    {
        "stage_name": "Michael Brown",
        "bio": "Everyman performer perfect for relatable characters. Natural and authentic in everyday scenarios.",
        "specialties": ["dramatic", "slice_of_life", "comedic"],
        "aci_score": 85.1,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 320,
        "completed_bookings": 305,
        "profile_image": "https://randomuser.me/api/portraits/men/12.jpg",
    },
    # Mid tier performers (ACI 78-84)
    {
        "stage_name": "Isabella Garcia",
        "bio": "Rising star with fresh perspective. Brings youthful energy to contemporary content.",
        "specialties": ["comedic", "romantic", "drama"],
        "aci_score": 84.5,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 290,
        "completed_bookings": 272,
        "profile_image": "https://randomuser.me/api/portraits/women/13.jpg",
    },
    {
        "stage_name": "Alex Turner",
        "bio": "Sci-fi and futuristic specialist. Comfortable with technical and high-concept performances.",
        "specialties": ["sci_fi", "action", "thriller"],
        "aci_score": 83.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 265,
        "completed_bookings": 248,
        "profile_image": "https://randomuser.me/api/portraits/men/14.jpg",
    },
    {
        "stage_name": "Mei Lin",
        "bio": "Emotional range specialist. Can deliver subtle nuance or explosive dramatic moments.",
        "specialties": ["dramatic", "romantic", "thriller"],
        "aci_score": 82.7,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 245,
        "completed_bookings": 228,
        "profile_image": "https://randomuser.me/api/portraits/women/15.jpg",
    },
    {
        "stage_name": "Jordan Price",
        "bio": "Youth market specialist. Authentic performances for teen and young adult content.",
        "specialties": ["comedic", "drama", "coming_of_age"],
        "aci_score": 81.9,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 225,
        "completed_bookings": 210,
        "profile_image": "https://randomuser.me/api/portraits/men/16.jpg",
    },
    {
        "stage_name": "Aisha Patel",
        "bio": "Cultural storytelling specialist. Brings authenticity to diverse narratives.",
        "specialties": ["dramatic", "cultural", "family"],
        "aci_score": 81.3,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 210,
        "completed_bookings": 195,
        "profile_image": "https://randomuser.me/api/portraits/women/17.jpg",
    },
    {
        "stage_name": "Chris Anderson",
        "bio": "Commercial and corporate specialist. Professional presence for business content.",
        "specialties": ["corporate", "commercial", "educational"],
        "aci_score": 80.6,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 195,
        "completed_bookings": 182,
        "profile_image": "https://randomuser.me/api/portraits/men/18.jpg",
    },
    {
        "stage_name": "Sarah Mitchell",
        "bio": "Children's content specialist. Warm and engaging performances for family audiences.",
        "specialties": ["family", "animation", "educational"],
        "aci_score": 79.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 180,
        "completed_bookings": 168,
        "profile_image": "https://randomuser.me/api/portraits/women/19.jpg",
    },
    {
        "stage_name": "Hassan Ali",
        "bio": "Action and adventure specialist with stunt training. High-intensity performances.",
        "specialties": ["action", "stunts", "adventure"],
        "aci_score": 79.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 168,
        "completed_bookings": 155,
        "profile_image": "https://randomuser.me/api/portraits/men/20.jpg",
    },
    # Synthetic performers (AI-generated)
    {
        "stage_name": "NOVA-7",
        "bio": "High-fidelity synthetic performer optimized for consistent character delivery. 24/7 availability.",
        "specialties": ["corporate", "educational", "commercial"],
        "aci_score": 88.5,
        "performer_type": PerformerType.SYNTHETIC,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 2500,
        "completed_bookings": 2495,
        "profile_image": "https://randomuser.me/api/portraits/lego/1.jpg",
    },
    {
        "stage_name": "ARIA-X",
        "bio": "Expressive synthetic performer with advanced emotional range algorithms.",
        "specialties": ["dramatic", "romantic", "family"],
        "aci_score": 86.2,
        "performer_type": PerformerType.SYNTHETIC,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 2100,
        "completed_bookings": 2090,
        "profile_image": "https://randomuser.me/api/portraits/lego/2.jpg",
    },
    {
        "stage_name": "TITAN-3",
        "bio": "Action-optimized synthetic performer. Perfect for high-intensity sequences.",
        "specialties": ["action", "stunts", "sci_fi"],
        "aci_score": 84.8,
        "performer_type": PerformerType.SYNTHETIC,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 1850,
        "completed_bookings": 1842,
        "profile_image": "https://randomuser.me/api/portraits/lego/3.jpg",
    },
    # Lower-mid tier (ACI 72-78)
    {
        "stage_name": "Olivia Foster",
        "bio": "Emerging talent with natural screen presence. Growing portfolio of diverse work.",
        "specialties": ["dramatic", "comedic", "indie"],
        "aci_score": 77.5,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 145,
        "completed_bookings": 132,
        "profile_image": "https://randomuser.me/api/portraits/women/21.jpg",
    },
    {
        "stage_name": "Daniel Lee",
        "bio": "Theater background with strong emotional commitment. Building screen experience.",
        "specialties": ["dramatic", "period", "musical"],
        "aci_score": 76.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 135,
        "completed_bookings": 122,
        "profile_image": "https://randomuser.me/api/portraits/men/22.jpg",
    },
    {
        "stage_name": "Rachel Green",
        "bio": "Comedy specialist with improv background. Quick thinking and creative.",
        "specialties": ["comedic", "improv", "sketch"],
        "aci_score": 75.9,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 125,
        "completed_bookings": 112,
        "profile_image": "https://randomuser.me/api/portraits/women/23.jpg",
    },
    {
        "stage_name": "Kevin Zhang",
        "bio": "Tech-savvy performer comfortable with motion capture equipment. Gaming content specialist.",
        "specialties": ["gaming", "animation", "action"],
        "aci_score": 75.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 118,
        "completed_bookings": 105,
        "profile_image": "https://randomuser.me/api/portraits/men/24.jpg",
    },
    {
        "stage_name": "Maria Santos",
        "bio": "Telenovela style specialist. Passionate and expressive performances.",
        "specialties": ["dramatic", "romantic", "cultural"],
        "aci_score": 74.4,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 110,
        "completed_bookings": 98,
        "profile_image": "https://randomuser.me/api/portraits/women/25.jpg",
    },
    {
        "stage_name": "Jake Williams",
        "bio": "Sports and athletic content specialist. High energy and physical performances.",
        "specialties": ["sports", "action", "commercial"],
        "aci_score": 73.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.PENDING,
        "total_bookings": 95,
        "completed_bookings": 85,
        "profile_image": "https://randomuser.me/api/portraits/men/26.jpg",
    },
    {
        "stage_name": "Emily Chen",
        "bio": "ASMR and gentle content specialist. Soothing presence for relaxation content.",
        "specialties": ["asmr", "educational", "wellness"],
        "aci_score": 73.1,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 88,
        "completed_bookings": 80,
        "profile_image": "https://randomuser.me/api/portraits/women/27.jpg",
    },
    {
        "stage_name": "Tyler Brooks",
        "bio": "Vlogger and influencer style specialist. Natural and relatable on camera.",
        "specialties": ["vlog", "commercial", "social"],
        "aci_score": 72.5,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 82,
        "completed_bookings": 74,
        "profile_image": "https://randomuser.me/api/portraits/men/28.jpg",
    },
    # Newer performers (ACI 65-72)
    {
        "stage_name": "Zara Ahmed",
        "bio": "Fashion and lifestyle content creator. Elegant and stylish performances.",
        "specialties": ["fashion", "commercial", "lifestyle"],
        "aci_score": 71.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 75,
        "completed_bookings": 68,
        "profile_image": "https://randomuser.me/api/portraits/women/29.jpg",
    },
    {
        "stage_name": "Brandon Moore",
        "bio": "Voice-focused performer. Excellent lip sync and dialogue delivery.",
        "specialties": ["voice", "dialogue", "dramatic"],
        "aci_score": 70.9,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 68,
        "completed_bookings": 62,
        "profile_image": "https://randomuser.me/api/portraits/men/30.jpg",
    },
    {
        "stage_name": "Lily Park",
        "bio": "K-content specialist. Familiar with K-drama and K-pop performance styles.",
        "specialties": ["k_content", "musical", "romantic"],
        "aci_score": 70.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 62,
        "completed_bookings": 56,
        "profile_image": "https://randomuser.me/api/portraits/women/31.jpg",
    },
    {
        "stage_name": "Antonio Rossi",
        "bio": "European cinema style. Sophisticated and artistic approach to performance.",
        "specialties": ["arthouse", "dramatic", "period"],
        "aci_score": 69.5,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.PENDING,
        "total_bookings": 55,
        "completed_bookings": 49,
        "profile_image": "https://randomuser.me/api/portraits/men/32.jpg",
    },
    {
        "stage_name": "Jasmine Taylor",
        "bio": "Versatile newcomer with theater training. Eager to take on challenging roles.",
        "specialties": ["dramatic", "musical", "comedic"],
        "aci_score": 68.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 48,
        "completed_bookings": 43,
        "profile_image": "https://randomuser.me/api/portraits/women/33.jpg",
    },
    {
        "stage_name": "Derek Johnson",
        "bio": "Reality TV and unscripted content specialist. Authentic reactions.",
        "specialties": ["reality", "unscripted", "comedic"],
        "aci_score": 68.1,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 42,
        "completed_bookings": 38,
        "profile_image": "https://randomuser.me/api/portraits/men/34.jpg",
    },
    {
        "stage_name": "Samantha Cole",
        "bio": "Health and fitness content creator. Energetic and motivational performances.",
        "specialties": ["fitness", "wellness", "commercial"],
        "aci_score": 67.4,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 38,
        "completed_bookings": 34,
        "profile_image": "https://randomuser.me/api/portraits/women/35.jpg",
    },
    {
        "stage_name": "Nathan Cross",
        "bio": "Thriller and suspense specialist. Creates tension through subtle performance.",
        "specialties": ["thriller", "horror", "dramatic"],
        "aci_score": 66.7,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.PENDING,
        "total_bookings": 35,
        "completed_bookings": 31,
        "profile_image": "https://randomuser.me/api/portraits/men/36.jpg",
    },
    {
        "stage_name": "Grace Kim",
        "bio": "Animation voice and motion specialist. Brings cartoon characters to life.",
        "specialties": ["animation", "voice", "family"],
        "aci_score": 66.0,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 32,
        "completed_bookings": 28,
        "profile_image": "https://randomuser.me/api/portraits/women/37.jpg",
    },
    {
        "stage_name": "Victor Romano",
        "bio": "Villain and antagonist specialist. Compelling antagonist performances.",
        "specialties": ["villain", "dramatic", "action"],
        "aci_score": 65.3,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 28,
        "completed_bookings": 25,
        "profile_image": "https://randomuser.me/api/portraits/men/38.jpg",
    },
    # Entry level performers (ACI 55-65)
    {
        "stage_name": "Mia Wong",
        "bio": "Recent graduate with film school training. Fresh perspective and enthusiasm.",
        "specialties": ["indie", "dramatic", "experimental"],
        "aci_score": 64.2,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 22,
        "completed_bookings": 19,
        "profile_image": "https://randomuser.me/api/portraits/women/39.jpg",
    },
    {
        "stage_name": "Lucas Silva",
        "bio": "Latin content specialist. Passionate and expressive performance style.",
        "specialties": ["cultural", "romantic", "musical"],
        "aci_score": 63.5,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.PENDING,
        "total_bookings": 18,
        "completed_bookings": 16,
        "profile_image": "https://randomuser.me/api/portraits/men/40.jpg",
    },
    {
        "stage_name": "Amy Roberts",
        "bio": "Documentary and educational content creator. Clear and engaging delivery.",
        "specialties": ["documentary", "educational", "corporate"],
        "aci_score": 62.8,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 15,
        "completed_bookings": 13,
        "profile_image": "https://randomuser.me/api/portraits/women/41.jpg",
    },
    {
        "stage_name": "Josh Patterson",
        "bio": "Gaming and esports content creator. High energy and competitive spirit.",
        "specialties": ["gaming", "esports", "streaming"],
        "aci_score": 61.1,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 12,
        "completed_bookings": 10,
        "profile_image": "https://randomuser.me/api/portraits/men/42.jpg",
    },
    {
        "stage_name": "Sophie Martin",
        "bio": "Cooking and lifestyle content specialist. Warm and inviting presence.",
        "specialties": ["cooking", "lifestyle", "tutorial"],
        "aci_score": 59.4,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.PENDING,
        "total_bookings": 10,
        "completed_bookings": 8,
        "profile_image": "https://randomuser.me/api/portraits/women/43.jpg",
    },
    {
        "stage_name": "Ben Carter",
        "bio": "New performer building portfolio. Eager to learn and grow.",
        "specialties": ["general", "commercial", "social"],
        "aci_score": 57.7,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 8,
        "completed_bookings": 7,
        "profile_image": "https://randomuser.me/api/portraits/men/44.jpg",
    },
    {
        "stage_name": "Hannah Lewis",
        "bio": "Starting performer with background in dance. Graceful movement.",
        "specialties": ["dance", "musical", "animation"],
        "aci_score": 56.0,
        "performer_type": PerformerType.HUMAN,
        "verification_status": PerformerVerification.PENDING,
        "total_bookings": 6,
        "completed_bookings": 5,
        "profile_image": "https://randomuser.me/api/portraits/women/45.jpg",
    },
    {
        "stage_name": "PIXEL-1",
        "bio": "Entry-level synthetic performer for basic content needs.",
        "specialties": ["basic", "commercial", "template"],
        "aci_score": 72.0,
        "performer_type": PerformerType.SYNTHETIC,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 850,
        "completed_bookings": 845,
        "profile_image": "https://randomuser.me/api/portraits/lego/4.jpg",
    },
    {
        "stage_name": "ECHO-2",
        "bio": "Budget-friendly synthetic performer. Reliable for high-volume content.",
        "specialties": ["commercial", "social", "educational"],
        "aci_score": 70.5,
        "performer_type": PerformerType.SYNTHETIC,
        "verification_status": PerformerVerification.VERIFIED,
        "total_bookings": 1200,
        "completed_bookings": 1195,
        "profile_image": "https://randomuser.me/api/portraits/lego/5.jpg",
    },
]


def _generate_pricing(aci_score: float, performer_type: PerformerType) -> dict:
    """Generate pricing based on ACI score and performer type."""
    base_multiplier = aci_score / 70  # Normalize around 70 ACI

    if performer_type == PerformerType.SYNTHETIC:
        # Synthetic performers are cheaper
        base_multiplier *= 0.5

    return {
        "blink": round(5.0 * base_multiplier, 2),
        "deep": round(25.0 * base_multiplier, 2),
        "epic_per_minute": round(10.0 * base_multiplier, 2),
        "auction_minimum": round(50.0 * base_multiplier, 2),
    }


def _generate_motion_capabilities(performer_type: PerformerType, aci_score: float) -> dict:
    """Generate motion capabilities based on performer type and score."""
    base_capabilities = {
        "supports_liveportrait": True,
        "supports_roop_gs_anim": aci_score > 75,
        "face_tracking_quality": "high" if aci_score > 85 else "medium" if aci_score > 70 else "standard",
        "hand_tracking": aci_score > 65,
        "body_tracking": aci_score > 80,
    }

    if performer_type == PerformerType.SYNTHETIC:
        base_capabilities["supported_resolutions"] = ["480p", "720p", "1080p", "4k"]
        base_capabilities["max_take_duration_seconds"] = 7200  # 2 hours
    else:
        resolutions = ["480p", "720p"]
        if aci_score > 70:
            resolutions.append("1080p")
        if aci_score > 85:
            resolutions.append("4k")
        base_capabilities["supported_resolutions"] = resolutions
        base_capabilities["max_take_duration_seconds"] = 1200 if aci_score > 80 else 600

    return base_capabilities


def _calculate_earnings(total_bookings: int, aci_score: float) -> tuple[float, float]:
    """Calculate earnings based on bookings and ACI score."""
    avg_booking_value = 15.0 * (aci_score / 70)  # Higher ACI = higher value bookings
    total_earnings = total_bookings * avg_booking_value
    lifetime_earnings = total_earnings * 1.2  # Some historical earnings
    return round(total_earnings, 2), round(lifetime_earnings, 2)


def _get_availability(total_bookings: int) -> PerformerAvailability:
    """Determine availability status based on activity."""
    if total_bookings > 500:
        # Busy performers are sometimes unavailable
        return random.choice([
            PerformerAvailability.AVAILABLE,
            PerformerAvailability.AVAILABLE,
            PerformerAvailability.BUSY,
        ])
    elif total_bookings > 100:
        return PerformerAvailability.AVAILABLE
    elif total_bookings > 20:
        return random.choice([
            PerformerAvailability.AVAILABLE,
            PerformerAvailability.OFFLINE,
        ])
    else:
        return random.choice([
            PerformerAvailability.AVAILABLE,
            PerformerAvailability.OFFLINE,
            PerformerAvailability.OFFLINE,
        ])


async def seed_performers(session: AsyncSession, force: bool = False) -> list[Performer]:
    """
    Seed the database with sample performers.

    Args:
        session: Database session
        force: If True, delete existing performers and reseed

    Returns:
        List of created Performer objects
    """
    # Check if performers already exist
    result = await session.execute(select(Performer).limit(1))
    existing = result.scalar_one_or_none()

    if existing and not force:
        print("Performers already exist. Use force=True to reseed.")
        return []

    if force and existing:
        # Delete existing performers
        await session.execute(Performer.__table__.delete())
        print("Deleted existing performers.")

    created_performers = []
    now = datetime.now(timezone.utc)

    for data in SAMPLE_PERFORMERS:
        # Calculate derived values
        total_earnings, lifetime_earnings = _calculate_earnings(
            data["total_bookings"], data["aci_score"]
        )

        # Determine availability
        availability = _get_availability(data["total_bookings"])

        # Generate pricing and capabilities
        pricing = _generate_pricing(data["aci_score"], data["performer_type"])
        motion_capabilities = _generate_motion_capabilities(
            data["performer_type"], data["aci_score"]
        )

        # Calculate join date based on bookings (more bookings = joined earlier)
        days_ago = min(365 * 3, data["total_bookings"] * 2)  # Max 3 years
        joined_at = now - timedelta(days=days_ago)

        # Calculate last active time
        if availability == PerformerAvailability.AVAILABLE:
            last_active = now - timedelta(hours=random.randint(1, 24))
        elif availability == PerformerAvailability.BUSY:
            last_active = now - timedelta(minutes=random.randint(5, 60))
        else:
            last_active = now - timedelta(days=random.randint(1, 30))

        performer = Performer(
            id=uuid4(),
            stage_name=data["stage_name"],
            bio=data["bio"],
            specialties=data["specialties"],
            performer_type=data["performer_type"],
            verification_status=data["verification_status"],
            availability_status=availability,
            aci_score=data["aci_score"],
            total_bookings=data["total_bookings"],
            completed_bookings=data["completed_bookings"],
            total_earnings_usd=total_earnings,
            lifetime_earnings_usd=lifetime_earnings,
            pricing=pricing,
            motion_capabilities=motion_capabilities,
            profile_image_path=data.get("profile_image"),
            joined_at=joined_at,
            last_active_at=last_active,
            is_active=True,
            created_at=joined_at,
            updated_at=now,
        )

        # Update revenue tier based on earnings
        performer.update_revenue_tier()

        session.add(performer)
        created_performers.append(performer)

    await session.commit()
    print(f"Created {len(created_performers)} performers.")

    return created_performers


async def main():
    """Run performer seeding as standalone script."""
    from scenemachine.database import get_async_session

    async with get_async_session() as session:
        performers = await seed_performers(session, force=True)
        print(f"\nSeeded {len(performers)} performers:")
        for p in performers[:5]:
            print(f"  - {p.stage_name} (ACI: {p.aci_score:.1f})")
        if len(performers) > 5:
            print(f"  ... and {len(performers) - 5} more")


if __name__ == "__main__":
    asyncio.run(main())
