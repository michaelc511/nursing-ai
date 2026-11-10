# API rules
- Routes are thin: parse input → call one `services/` function → return. No business logic here.
- Request/response models live in `app/schemas/`; errors come from `app.errors` as JSON `{"detail": ...}`.
- Auth via `Depends(current_user)`; role rules are enforced in services, not routes.
- See the `building-endpoints` skill.
