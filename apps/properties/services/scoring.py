"""
Scoring engine for Property Investment Potential and Passport Trust Scores.
"""

def calculate_property_investment_score(property_listing):
    """
    Computes a 0-100 algorithmic score assessing the investment potential of a listing.
    """
    title_score = 15
    if property_listing.has_c_of_o:
        title_score = 35
    elif property_listing.has_survey_plan:
        title_score = 25
    if property_listing.is_title_verified:
        title_score = min(35, title_score + 5)

    infra_score = 10
    if property_listing.has_electricity:
        infra_score += 5
    if property_listing.has_water:
        infra_score += 4
    if property_listing.has_drainage:
        infra_score += 3
    if property_listing.has_security:
        infra_score += 3
    infra_score = min(25, infra_score)

    seller_score = 10
    seller = property_listing.realtor or property_listing.landlord or property_listing.developer
    if seller and getattr(seller, 'is_verified', False):
        seller_score = 20

    value_score = 14
    if property_listing.latitude and property_listing.longitude:
        value_score += 6
    value_score = min(20, value_score)

    total_score = title_score + infra_score + seller_score + value_score

    return {
        'total_score': total_score,
        'rating_label': 'Strong Growth Potential' if total_score >= 75 else ('Moderate Potential' if total_score >= 55 else 'Standard Yield'),
        'title_score': title_score,
        'infra_score': infra_score,
        'seller_score': seller_score,
        'value_score': value_score,
    }
