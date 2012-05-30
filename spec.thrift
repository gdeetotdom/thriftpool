namespace * broker

struct Task {
  1: string name,
  2: string workload
}

struct Result {
  1: string data
}

service Broker {
  Result execute(1: Task task)
}