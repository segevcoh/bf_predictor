# Body fat predictor

Code for body fat predictor, which can be found here: 
https://huggingface.co/spaces/SegevC/bf_predictor..

### Extracting the data
We begin by scrapping the subreddit "guessmybf". 
We go over posts which contain photos, download them, and save any 
relevant data from the post in a csv file (for example we save the different
comments for a given post, the post score, the id of post's author and so on) - 
This is done via the scrape_from_reddit method in the file "reddit_bf_scraping.py".
This gives us about 1800 labeled photos 

### Cleaning odd data - Part I
After an initial cleanup of the raw data (e.g. deleting comments 
which obviously don't refer to the post bf%). We divide all photos into 
different folders - given by the  range a certain picture fall into, e.g. pictures
of users who were deemed to have 13% bf are put in a folder named "11-14.9%" and pictures
of users who were deemed to have 6% are  put in a folder named "3.0-6.9" and so on..
We then quickly  go over this data with our eyes to check for abnormalities 
(for example, we check for people in the highest and lowest bf% and see if there are 
any pictures which were misclassified).
We then look and the data's distribution, and see if it indeed makes sense

![alt text](bf_histogram_after_eyebaling.jpg)

and indeed a quick check in the internet yields a similar trend to the one we 
know bf% distributes in the general western population 

### Cleaning odd data - Part II
Now that we have an initial data to work with, we use transfer learning on the resnet34
NN for 30 epochs using a learning rate of 1e-2 (this lr was chosen using the lr_find() 
method from fastai) - The loss is measured by MSE.
![alt text](loss_after_1_train.jpg)
In retrospect it might have been better to use a different NN or train this one for 
much less epochs. We now use this trained NN, to find anomalies in our data. 
And indeed after checking the model's prediction on the training set we have 112 instances
in which the model's prediction was off at about 4%. Going over those anomalies we see
that 41 of them should not be considered as part of the training data - (e.g. picture
of dexa scans, of a single limb etc..)
