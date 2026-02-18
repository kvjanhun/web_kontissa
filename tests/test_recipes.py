class TestListRecipes:
    def test_list_empty(self, logged_in_user):
        res = logged_in_user.get("/api/recipes")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_list_with_data(self, logged_in_user, sample_recipe):
        res = logged_in_user.get("/api/recipes")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["slug"] == "pancakes"
        # List endpoint should not include children
        assert "ingredients" not in data[0]
        assert "steps" not in data[0]

    def test_list_unauthenticated(self, client, app):
        res = client.get("/api/recipes")
        assert res.status_code == 401

    def test_search_by_title(self, logged_in_user, sample_recipe):
        res = logged_in_user.get("/api/recipes?q=pancake")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["slug"] == "pancakes"

    def test_search_by_ingredient(self, logged_in_user, sample_recipe):
        res = logged_in_user.get("/api/recipes?q=flour")
        data = res.get_json()
        assert len(data) == 1

    def test_search_no_match(self, logged_in_user, sample_recipe):
        res = logged_in_user.get("/api/recipes?q=sushi")
        data = res.get_json()
        assert len(data) == 0

    def test_filter_by_category(self, logged_in_user, sample_recipe):
        res = logged_in_user.get("/api/recipes?category=Breakfast")
        data = res.get_json()
        assert len(data) == 1

    def test_filter_category_no_match(self, logged_in_user, sample_recipe):
        res = logged_in_user.get("/api/recipes?category=Dessert")
        data = res.get_json()
        assert len(data) == 0


class TestGetRecipe:
    def test_get_by_slug(self, logged_in_user, sample_recipe):
        res = logged_in_user.get(f"/api/recipes/{sample_recipe['slug']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["title"] == "Pancakes"
        assert len(data["ingredients"]) == 3
        assert len(data["steps"]) == 3
        assert data["ingredients"][0]["name"] == "Flour"
        assert data["steps"][0]["content"] == "Mix dry ingredients"

    def test_get_not_found(self, logged_in_user):
        res = logged_in_user.get("/api/recipes/nonexistent")
        assert res.status_code == 404

    def test_get_unauthenticated(self, client, app, sample_recipe):
        res = client.get(f"/api/recipes/{sample_recipe['slug']}")
        assert res.status_code == 401


class TestCreateRecipe:
    def _recipe_payload(self, **overrides):
        payload = {
            "title": "Omelette",
            "category": "Breakfast",
            "ingredients": [
                {"name": "Eggs", "amount": "3"},
                {"name": "Cheese", "amount": "50", "unit": "g"},
            ],
            "steps": [
                {"content": "Beat eggs"},
                {"content": "Cook in pan"},
            ],
        }
        payload.update(overrides)
        return payload

    def test_create_success(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload())
        assert res.status_code == 201
        data = res.get_json()
        assert data["title"] == "Omelette"
        assert data["slug"] == "omelette"
        assert data["category"] == "Breakfast"
        assert len(data["ingredients"]) == 2
        assert len(data["steps"]) == 2

    def test_create_unauthenticated(self, client, app):
        res = client.post("/api/recipes", json=self._recipe_payload())
        assert res.status_code == 401

    def test_create_missing_title(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(title=""))
        assert res.status_code == 400

    def test_create_invalid_category(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(category="Invalid"))
        assert res.status_code == 400

    def test_create_no_ingredients(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(ingredients=[]))
        assert res.status_code == 400

    def test_create_no_steps(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(steps=[]))
        assert res.status_code == 400

    def test_create_ingredient_missing_name(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(
            ingredients=[{"amount": "1"}]
        ))
        assert res.status_code == 400

    def test_create_empty_step(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(
            steps=[{"content": ""}]
        ))
        assert res.status_code == 400

    def test_create_no_category(self, logged_in_user):
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload(category=None))
        assert res.status_code == 201
        assert res.get_json()["category"] is None

    def test_slug_dedup(self, logged_in_user):
        logged_in_user.post("/api/recipes", json=self._recipe_payload())
        res = logged_in_user.post("/api/recipes", json=self._recipe_payload())
        assert res.status_code == 201
        assert res.get_json()["slug"] == "omelette-2"


class TestUpdateRecipe:
    def _update_payload(self):
        return {
            "title": "Updated Pancakes",
            "category": "Brunch" if False else "Lunch",
            "ingredients": [
                {"name": "Flour", "amount": "3", "unit": "cups"},
            ],
            "steps": [
                {"content": "Mix and cook"},
            ],
        }

    def test_update_success(self, logged_in_user, sample_recipe):
        res = logged_in_user.put(
            f"/api/recipes/{sample_recipe['id']}",
            json=self._update_payload(),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["title"] == "Updated Pancakes"
        assert data["slug"] == "updated-pancakes"
        assert len(data["ingredients"]) == 1
        assert len(data["steps"]) == 1

    def test_update_not_found(self, logged_in_user):
        res = logged_in_user.put("/api/recipes/9999", json=self._update_payload())
        assert res.status_code == 404

    def test_update_unauthenticated(self, client, app, sample_recipe):
        res = client.put(
            f"/api/recipes/{sample_recipe['id']}",
            json=self._update_payload(),
        )
        assert res.status_code == 401

    def test_update_invalid_category(self, logged_in_user, sample_recipe):
        payload = self._update_payload()
        payload["category"] = "BadCategory"
        res = logged_in_user.put(f"/api/recipes/{sample_recipe['id']}", json=payload)
        assert res.status_code == 400

    def test_update_same_title_keeps_slug(self, logged_in_user, sample_recipe):
        payload = self._update_payload()
        payload["title"] = "Pancakes"
        res = logged_in_user.put(f"/api/recipes/{sample_recipe['id']}", json=payload)
        assert res.status_code == 200
        assert res.get_json()["slug"] == "pancakes"


class TestDeleteRecipe:
    def test_delete_success(self, logged_in_user, sample_recipe):
        res = logged_in_user.delete(f"/api/recipes/{sample_recipe['id']}")
        assert res.status_code == 200

        res = logged_in_user.get("/api/recipes")
        assert res.get_json() == []

    def test_delete_not_found(self, logged_in_user):
        res = logged_in_user.delete("/api/recipes/9999")
        assert res.status_code == 404

    def test_delete_unauthenticated(self, client, app, sample_recipe):
        res = client.delete(f"/api/recipes/{sample_recipe['id']}")
        assert res.status_code == 401


class TestCategories:
    def test_get_categories(self, logged_in_user):
        res = logged_in_user.get("/api/recipes/categories")
        assert res.status_code == 200
        data = res.get_json()
        assert "Breakfast" in data
        assert "Dinner" in data
        assert len(data) == 8

    def test_categories_unauthenticated(self, client, app):
        res = client.get("/api/recipes/categories")
        assert res.status_code == 401
