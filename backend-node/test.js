require('dotenv').config();
const mongoose = require('mongoose');
const User = require('./models/User');

mongoose.connect(process.env.MONGO_URI).then(async () => {
  console.log('MongoDB connected');
  try {
    const user = await User.create({
      name: 'Test User',
      email: 'testuser99@gmail.com',
      password: 'test123456'
    });
    console.log('SUCCESS - User created:', user.name, user.email);
  } catch(e) {
    console.log('ERROR:', e.message);
  }
  process.exit(0);
}).catch(e => {
  console.log('DB ERROR:', e.message);
  process.exit(1);
});