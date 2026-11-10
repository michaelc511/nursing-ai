// Display names for roles (always capitalized in the UI).
export const ROLE_NAMES: Record<string, string> = {
  nurse: "Nurse", medical_director: "Medical Director", intake: "Intake Coordinator",
};
export const roleName = (role?: string | null) => (role ? ROLE_NAMES[role] ?? role : "");
