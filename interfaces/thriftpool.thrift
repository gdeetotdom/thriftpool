namespace * thriftpool.remote


service ThriftPool {
   void ping();
   string echoString(1: string s);
}
