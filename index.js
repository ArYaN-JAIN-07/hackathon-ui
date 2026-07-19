import express from "express"
import bodyparser from "body-parser"

const app = express();
const port = 4000;


app.use(bodyparser.urlencoded({extended :true}));

app.use(express.static("public"));

app.get("/" , (req , res) => {
    res.render("index.ejs");
})

// app.post("/predict" , (req.res) => {

// })


app.listen(port , (req , res) => {
    console.log(`The server is running on port ${port}`);
})