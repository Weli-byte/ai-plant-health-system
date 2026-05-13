// Mock auth — sadece prototip.
const KEY = "agri_user";

export type MockUser = { email: string; name: string };

export function getUser(): MockUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as MockUser) : null;
  } catch {
    return null;
  }
}

export function loginMock(email: string, name?: string) {
  const user: MockUser = {
    email,
    name: name?.trim() || email.split("@")[0] || "Çiftçi",
  };
  localStorage.setItem(KEY, JSON.stringify(user));
  return user;
}

export function logout() {
  localStorage.removeItem(KEY);
}
