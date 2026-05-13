// Mock auth — sadece prototip.
const KEY = "agri_user";

export type MockUser = {
  email: string;
  name: string;
  phone?: string;
  city?: string;
  district?: string;
  fieldSize?: number;
  crops?: string[];
  profileComplete?: boolean;
  backendUserId?: number;
};

export function getUser(): MockUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as MockUser) : null;
  } catch {
    return null;
  }
}

export function loginMock(email: string, name?: string): MockUser {
  const existing = getUser();
  const user: MockUser = {
    // Mevcut profil verilerini koru, sadece kimlik bilgilerini güncelle
    ...(existing?.email === email ? existing : {}),
    email,
    name: name?.trim() || email.split("@")[0] || "Çiftçi",
  };
  localStorage.setItem(KEY, JSON.stringify(user));
  return user;
}

export function saveProfile(fields: Partial<MockUser>): MockUser | null {
  const user = getUser();
  if (!user) return null;
  const updated: MockUser = { ...user, ...fields, profileComplete: true };
  localStorage.setItem(KEY, JSON.stringify(updated));
  return updated;
}

export function setBackendUserId(id: number): void {
  const user = getUser();
  if (!user) return;
  localStorage.setItem(KEY, JSON.stringify({ ...user, backendUserId: id }));
}

export function logout() {
  localStorage.removeItem(KEY);
}
