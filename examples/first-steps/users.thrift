namespace * org.stubs.users

struct UserProfile {
	1: i32 uid,
	2: string name,
}

service UserStorage {
	UserProfile retrieve(1: i32 uid)
}
