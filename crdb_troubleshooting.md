# CockroachDB Troubleshooting Guide
This guide is meant to assist troubleshooting various situations while running [CockroachDB](https://cockroachlabs.com).  Consider this a living document that provides treatments for common issues seen by customers running CockroachDB. 

## Troubleshooting Methodology 
The methology used will mirror what is done in the medical community.  When you are not feeling well you have certian **symptoms** which leads to **diagnosis** and **treatment**.  Each issue listed will walk through the same steps towards resolution.  Below is an example of this process:

* Symptoms
    * Description of problem
    * Observations
* Diagnosis
    * Drill down on the symptoms
    * Tools and techniques
    * Correlation of observations to formulate a treatment
* Treatment
    * May have multiple treatment options    
    * Define steps and observations towards resolution
        * Do *X* and observe *Y*
        * Do *K* and observe *LMNOP*

## Common Issues
Consider this a living repository that provides treatments for common aliments seen by customers running CockroachDB.  Please contribute and suggest your troubleshooting experiences.

* [Hot Single Range Queries](issues/hotrange/hot_singlerange_troubleshooting.md)
* [Delete Batching](issues/delete_batching/delete_batching.md)
