# scratch_test_recommender.py

from apps.api.models import UserConstraints, UserProfile
from apps.api.recommender import recommend_recipes_mvp


def main():
    # 1) Fake recipes as simple dicts
    recipes = [
        {
            "id": 1,
            "title": "Creamy Tomato Pasta",
            "ingredients": ["pasta", "tomato sauce", "cream", "parmesan"],
            "cuisine": "italian",
            "avg_rating": 4.5,
        },
        {
            "id": 2,
            "title": "Garlic Egg Fried Rice",
            "ingredients": ["rice", "eggs", "garlic", "soy sauce"],
            "cuisine": "asian",
            "avg_rating": 4.2,
        },
        {
            "id": 3,
            "title": "Peanut Noodles",
            "ingredients": ["noodles", "peanut butter", "soy sauce"],
            "cuisine": "asian",
            "avg_rating": 4.8,
        },
    ]

    # 2) Fake items in the house
    pantry_item_names = ["pasta", "tomato sauce", "parmesan", "eggs"]

    # 3) Constraints like dropdowns
    constraints = UserConstraints(
        cuisine=["italian", "asian"],
        mood="comfort",
        energy_level="low",
        include_ingredients=["pasta"],
        exclude_ingredients=[],
        diet_types=[],
    )

    # 4) Simple profile
    user_profile = UserProfile(
        allergies=["peanuts"],
        diet_types=[],
    )

    # 5) Call the recommender
    recs = recommend_recipes_mvp(
        recipes=recipes,
        pantry_item_names=pantry_item_names,
        constraints=constraints,
        user_profile=user_profile,
        top_k=5,
    )

    # 6) Print results
    print("Recommendations:")
    for r in recs:
        print(r)


if __name__ == "__main__":
    main()
